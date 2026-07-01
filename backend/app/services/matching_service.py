from typing import List, Dict, Any
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.resume import resume_repo
from app.repositories.job import job_repo
from app.repositories.application import application_repo
from app.repositories.user import user_repo
from app.services.openai_service import openai_service
from app.models.models import JobRecommendation, UserPreferences, ScoringConfig

class MatchingService:
    async def match_resume_to_jobs(
        self, db: AsyncSession, user_id: int, resume_version_id: int
    ) -> List[JobRecommendation]:
        # 1. Retrieve the resume version and its embedding
        version = await resume_repo.get_version(db, resume_version_id)
        if not version or not version.embedding:
            raise ValueError("Resume version or its vector embedding not found")

        resume_embedding = version.embedding.embedding
        
        # Extract skills for rule engine matching
        user_skills = {s.skill_name.lower() for s in version.skills}

        # 2. Retrieve user preferences
        prefs: UserPreferences = await user_repo.get_preferences(db, user_id)
        pref_locations = prefs.preferred_locations if prefs else None
        pref_job_types = prefs.preferred_job_types if prefs else None
        min_salary = prefs.min_salary if prefs else None
        pref_remote = prefs.is_remote if prefs else False
        company_exclusions = set(prefs.company_exclusions) if prefs and prefs.company_exclusions else set()

        # 3. Retrieve retrieval scoring configs (Default weights)
        weights = {
            "skill": 0.35,
            "experience": 0.15,
            "location": 0.15,
            "remote": 0.10,
            "salary": 0.10,
            "freshness": 0.15
        }

        # 4. Phase 1: Vector similarity search (Retrieve Top 100 jobs)
        candidate_jobs = await job_repo.get_jobs_by_vector_similarity(
            db, embedding=resume_embedding, limit=100
        )

        # 5. Phase 2: Rule Engine scoring (Filter down to Top 20)
        scored_jobs = []
        now = datetime.datetime.now(datetime.timezone.utc)

        for job, vector_score in candidate_jobs:
            # Check company exclusions
            if job.company.name in company_exclusions:
                continue

            # Skill overlap
            job_skills = {s.skill_name.lower() for s in job.skills}
            skill_score = 0.0
            if job_skills:
                matching_skills = user_skills.intersection(job_skills)
                skill_score = len(matching_skills) / len(job_skills)

            # Location match
            location_score = 1.0
            if pref_locations and job.location:
                location_score = 1.0 if any(loc.lower() in job.location.lower() for loc in pref_locations) else 0.2

            # Remote alignment
            remote_score = 1.0
            if pref_remote and not job.is_remote:
                remote_score = 0.3

            # Salary alignment
            salary_score = 1.0
            if min_salary and job.salary_min:
                salary_score = 1.0 if job.salary_min >= min_salary else 0.5

            # Freshness score (exponential decay based on days old)
            days_old = (now - job.created_at).days
            freshness_score = max(0.1, 1.0 - (days_old / 30.0)) # linearly decays to 0.1 after 30 days

            # Rule engine final score (Vector score + Rule scores weighted)
            # Vector score forms 40% of basic score, rules make up 60%
            weighted_rules = (
                (skill_score * weights["skill"]) +
                (location_score * weights["location"]) +
                (remote_score * weights["remote"]) +
                (salary_score * weights["salary"]) +
                (freshness_score * weights["freshness"])
            )
            final_score = (vector_score * 0.4) + (weighted_rules * 0.6)

            scored_jobs.append({
                "job": job,
                "score": round(final_score * 100, 2) # convert to percentage
            })

        # Sort jobs by final score descending and select top 20
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)
        top_20 = scored_jobs[:20]

        # 6. Phase 3: AI Match Explanation (Retrieve Top 10 recommendations)
        final_recommendations = []
        resume_summary = f"Skills: {', '.join(user_skills)}. Experience: {[e.get('title') for e in version.parsed_data.parsed_json.get('experience', [])]}"
        
        # We limit the AI calls to the top 10 recommended jobs to save tokens/speed up
        top_10 = top_20[:10]

        for item in top_10:
            job_obj = item["job"]
            score = item["score"]

            # Check if recommendation already exists in database
            existing = await application_repo.get_recommendation(db, user_id, job_obj.id)
            if existing:
                final_recommendations.append(existing)
                continue

            # Generate natural language match explanation
            job_summary = f"Title: {job_obj.title} at {job_obj.company.name}. Description: {job_obj.description}"
            explanation = await openai_service.explain_match(resume_summary, job_summary)

            rec_dict = {
                "user_id": user_id,
                "job_id": job_obj.id,
                "resume_version_id": resume_version_id,
                "score": score,
                "explanation": explanation,
                "is_saved": False,
                "is_dismissed": False
            }
            # Save to database
            recs_objs = await application_repo.save_recommendations(db, [rec_dict])
            final_recommendations.append(recs_objs[0])

        await db.commit()
        return final_recommendations

matching_service = MatchingService()
