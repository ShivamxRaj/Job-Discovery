from typing import List, Dict, Any
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.resume import resume_repo
from app.repositories.job import job_repo
from app.repositories.application import application_repo
from app.repositories.user import user_repo
from app.services.openai_service import openai_service
from app.models.models import JobRecommendation, UserPreferences, ScoringConfig
from app.services.normalization_service import NormalizationService

# Configurable diversity thresholds
TOP_K = 10
MAX_COMPANY_RESULTS_PER_TOP_K = 2
MAX_CATEGORY_RESULTS_PER_TOP_K = 3

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

        # Determine candidate category using multi-signal classifier
        cand_text = " ".join(user_skills).lower()
        if prefs and prefs.preferred_roles:
            cand_text += " " + " ".join(prefs.preferred_roles).lower()
        try:
            for exp in version.parsed_data.parsed_json.get("experience", []):
                if exp.get("title"):
                    cand_text += " " + exp.get("title").lower()
        except Exception:
            pass
            
        cand_title = ""
        if prefs and prefs.preferred_roles:
            cand_title = prefs.preferred_roles[0]
        elif version.parsed_data.parsed_json.get("experience"):
            cand_title = version.parsed_data.parsed_json.get("experience")[0].get("title", "")
        else:
            cand_title = "Software Engineer"
            
        candidate_category, candidate_conf = NormalizationService.classify_category(
            title=cand_title,
            skills=list(user_skills),
            description=cand_text
        )

        # 3. Retrieve retrieval scoring configs (Default weights)
        weights = {
            "role": 0.25,
            "skill": 0.20,
            "experience": 0.15,
            "location": 0.15,
            "remote": 0.10,
            "salary": 0.10,
            "freshness": 0.05
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

            # Multi-signal job classification
            job_skills_list = [s.skill_name for s in job.skills]
            job_category, job_conf = NormalizationService.classify_category(
                title=job.title,
                skills=job_skills_list,
                description=job.description,
                company_name=job.company.name,
                company_website=job.company.website,
                job_type=job.job_type
            )

            # Category similarity matching matrix
            category_score = 0.0
            if candidate_category == job_category:
                category_score = 1.0
            else:
                tech_categories = {"SOFTWARE_ENGINEERING", "AI_ML", "DATA_SCIENCE", "DEVOPS_CLOUD", "CYBERSECURITY", "BUSINESS_ANALYTICS"}
                if candidate_category in tech_categories and job_category in tech_categories:
                    if {candidate_category, job_category} <= {"SOFTWARE_ENGINEERING", "AI_ML"}:
                        category_score = 0.9
                    elif {candidate_category, job_category} <= {"SOFTWARE_ENGINEERING", "DEVOPS_CLOUD"}:
                        category_score = 0.8
                    elif {candidate_category, job_category} <= {"SOFTWARE_ENGINEERING", "CYBERSECURITY"}:
                        category_score = 0.8
                    elif {candidate_category, job_category} <= {"DATA_SCIENCE", "BUSINESS_ANALYTICS"}:
                        category_score = 0.8
                    elif {candidate_category, job_category} <= {"AI_ML", "DATA_SCIENCE"}:
                        category_score = 0.8
                    else:
                        category_score = 0.6
                else:
                    category_score = 0.0

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

            # Experience match
            experience_score = 1.0
            candidate_years = 0.0
            try:
                experience_list = version.parsed_data.parsed_json.get("experience", [])
                for exp in experience_list:
                    years = exp.get("years")
                    if years:
                        candidate_years += float(years)
            except Exception:
                candidate_years = 0.0

            # Determine required experience based on job title keywords
            job_title_lower = job.title.lower()
            if any(w in job_title_lower for w in ["senior", "sr.", "sr ", "lead", "principal", "architect"]):
                required_years = 5.0
            elif any(w in job_title_lower for w in ["junior", "jr.", "jr ", "associate", "intern", "entry"]):
                required_years = 1.0
            else:
                required_years = 3.0

            if candidate_years >= required_years:
                experience_score = 1.0
            else:
                experience_score = max(0.2, candidate_years / required_years)

            # Freshness score (linear decay based on days old)
            days_old = (now - job.created_at).days
            freshness_score = max(0.1, 1.0 - (days_old / 30.0))

            # Rule engine final score (Vector score + Rule scores weighted)
            weighted_rules = (
                (category_score * weights["role"]) +
                (skill_score * weights["skill"]) +
                (experience_score * weights["experience"]) +
                (location_score * weights["location"]) +
                (remote_score * weights["remote"]) +
                (salary_score * weights["salary"]) +
                (freshness_score * weights["freshness"])
            )
            final_score = (vector_score * 0.4) + (weighted_rules * 0.6)

            # Apply category compatibility penalty (gate)
            if category_score == 0.0:
                final_score *= 0.1

            scored_jobs.append({
                "job": job,
                "score": round(final_score * 100, 2),
                "category": job_category
            })

        # Sort jobs by final score descending
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)

        # Apply greedy diversity re-ranking (company and category limits)
        diverse_scored_jobs = []
        company_counts = {}
        category_counts = {}
        deferred_jobs = []

        for item in scored_jobs:
            job_obj = item["job"]
            company_name = job_obj.company.name if job_obj.company else "Unknown"
            cat = item["category"]

            comp_count = company_counts.get(company_name, 0)
            cat_count = category_counts.get(cat, 0)

            # Check dynamic diversity thresholds
            if comp_count < MAX_COMPANY_RESULTS_PER_TOP_K and cat_count < MAX_CATEGORY_RESULTS_PER_TOP_K:
                diverse_scored_jobs.append(item)
                company_counts[company_name] = comp_count + 1
                category_counts[cat] = cat_count + 1
            else:
                deferred_jobs.append(item)

        # Fill up to 20 if needed
        if len(diverse_scored_jobs) < 20:
            diverse_scored_jobs.extend(deferred_jobs[:20 - len(diverse_scored_jobs)])

        top_20 = diverse_scored_jobs[:20]

        # 6. Phase 3: Match Explanation (Retrieve Top TOP_K recommendations)
        final_recommendations = []
        resume_summary = f"Skills: {', '.join(user_skills)}. Experience: {[e.get('title') for e in version.parsed_data.parsed_json.get('experience', [])]}"
        
        top_k_jobs = top_20[:TOP_K]

        for item in top_k_jobs:
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
