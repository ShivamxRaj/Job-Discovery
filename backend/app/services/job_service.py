import httpx
import re
from typing import List, Dict, Any, Optional
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job import job_repo
from app.services.openai_service import openai_service
from app.models.models import Job, Company, JobSource
from app.core.config import settings


class JobService:
    async def resolve_canonical_company(self, db: AsyncSession, raw_name: str, website: Optional[str] = None) -> Company:
        from app.models.models import CanonicalCompany, CompanyAlias, Company
        from sqlalchemy.future import select
        from app.services.normalization_service import NormalizationService
        
        # 1. Clean and normalize name
        normalized_name, original_name = NormalizationService.normalize_company(raw_name)
        norm_key = normalized_name.lower()
        
        # Extract domain from website if present
        domain = None
        if website:
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', website)
            if domain_match:
                domain = domain_match.group(1).lower()

        canonical = None
        # 2. Try matching by domain first
        if domain:
            res = await db.execute(select(CanonicalCompany).where(CanonicalCompany.domain == domain))
            canonical = res.scalar_one_or_none()

        # 3. Try matching alias
        if not canonical:
            res = await db.execute(select(CompanyAlias).where(CompanyAlias.alias == original_name))
            alias_obj = res.scalar_one_or_none()
            if alias_obj:
                canonical = await db.get(CanonicalCompany, alias_obj.company_id)

        # 4. Try matching normalized name of canonical company
        if not canonical:
            res = await db.execute(select(CanonicalCompany).where(CanonicalCompany.normalized_name == norm_key))
            canonical = res.scalar_one_or_none()

        # 5. Create unverified CanonicalCompany and alias if not found
        if not canonical:
            try:
                async with db.begin_nested():
                    canonical = CanonicalCompany(
                        display_name=normalized_name,
                        normalized_name=norm_key,
                        domain=domain,
                        is_verified=False
                    )
                    db.add(canonical)
                    await db.flush()
                    
                    alias_obj = CompanyAlias(
                        alias=original_name,
                        company_id=canonical.id
                    )
                    db.add(alias_obj)
                    await db.flush()
            except Exception:
                res = await db.execute(select(CanonicalCompany).where(CanonicalCompany.normalized_name == norm_key))
                canonical = res.scalar_one_or_none()

        # 6. Get or create corresponding legacy Company record for FK compatibility
        company = await job_repo.get_company_by_name(db, norm_key)
        if not company:
            try:
                async with db.begin_nested():
                    company = Company(
                        name=original_name,
                        normalized_name=canonical.normalized_name,
                        website=website,
                        logo_url=None
                    )
                    db.add(company)
                    await db.flush()
            except Exception:
                res = await db.execute(select(Company).where(Company.normalized_name == norm_key))
                company = res.scalar_one_or_none()

        return company

    def normalize_company_name(self, name: str) -> str:
        """Standardize company name (e.g. Google Inc. -> Google)"""
        name = name.strip()
        suffixes = ["inc", "inc.", "llc", "llc.", "ltd", "ltd.", "corp", "corporation", "co", "co.", "gmbh"]
        words = name.split()
        if len(words) > 1 and words[-1].lower() in suffixes:
            words.pop()
        return " ".join(words)

    def normalize_job_title(self, title: str) -> str:
        """Standardize job title (e.g. Sr. React Dev -> Senior React Developer)"""
        title = title.strip()
        replacements = {
            "sr.": "Senior",
            "sr": "Senior",
            "jr.": "Junior",
            "jr": "Junior",
            "dev": "Developer",
            "eng": "Engineer",
            "swe": "Software Engineer",
            "fullstack": "Full Stack",
            "frontend": "Front End",
            "backend": "Back End"
        }
        words = title.split()
        normalized_words = [replacements.get(w.lower().rstrip(",:"), w) for w in words]
        return " ".join(normalized_words)

    async def ingest_job(
        self, db: AsyncSession, raw_job: Dict[str, Any], source_name: str
    ) -> Optional[Job]:
        """Ingest, normalize, deduplicate, and store a job posting"""
        from app.services.normalization_service import NormalizationService
        from app.services.skill_service import SkillService
        from app.services.deduplication_service import DeduplicationService
        from app.models.models import JobSkill

        # 1. URL uniqueness check
        url = raw_job.get("url")
        if not url:
            return None
            
        existing_job = await job_repo.get_by_url(db, url)
        if existing_job:
            return existing_job

        # 2. Get/Create Job Source
        source = await job_repo.get_source_by_name(db, source_name)
        if not source:
            source = JobSource(name=source_name, parser_type="API")
            db.add(source)
            await db.flush()

        # 3. Company resolution & normalization
        raw_company_name = raw_job.get("company_name", "Unknown Company")
        company = await self.resolve_canonical_company(db, raw_company_name, raw_job.get("company_website"))
        original_company_name = raw_company_name
        normalized_company_name = NormalizationService.normalize_company(raw_company_name)[0]

        # 4. Title normalization
        raw_title = raw_job.get("title", "Job Posting")
        normalized_title, original_title, title_confidence = NormalizationService.normalize_title(raw_title)

        # 5. Type, Location, Salary Parsing
        raw_job_type = raw_job.get("job_type", "Full-time")
        employment_type = NormalizationService.parse_employment_type(raw_job_type)

        raw_location = raw_job.get("location", "Remote")
        city, state, country, is_remote, remote_type, location_confidence = NormalizationService.parse_location(raw_location)

        raw_salary = raw_job.get("salary")
        if not raw_salary:
            raw_salary_min = raw_job.get("salary_min")
            raw_salary_max = raw_job.get("salary_max")
            raw_currency = raw_job.get("currency")
            salary_min = float(raw_salary_min) if raw_salary_min is not None else None
            salary_max = float(raw_salary_max) if raw_salary_max is not None else None
            currency = raw_currency
            salary_period = "yearly"
            salary_confidence = 1.0 if (currency and (salary_min is not None or salary_max is not None)) else 0.1
        else:
            salary_min, salary_max, currency, salary_period, salary_confidence = NormalizationService.parse_salary(raw_salary)

        # 6. Category classification
        job_category, category_confidence = NormalizationService.classify_category(
            title=original_title,
            skills=raw_job.get("skills", []),
            description=raw_job.get("description", ""),
            company_name=company.name,
            company_website=company.website,
            job_type=raw_job_type
        )

        # Create Job Record
        job = Job(
            title=original_title,
            normalized_title=normalized_title,
            description=raw_job.get("description", ""),
            company_id=company.id,
            location=raw_location,
            job_type=raw_job_type,
            employment_type=employment_type,
            city=city,
            state=state,
            country=country,
            remote_type=remote_type,
            is_remote=is_remote,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            salary_period=salary_period,
            original_company_name=original_company_name,
            normalized_company_name=normalized_company_name,
            source_id=source.id,
            url=url,
            created_at=raw_job.get("created_at", datetime.datetime.now(datetime.timezone.utc)),
            is_seed_data=raw_job.get("is_seed_data", False),
            data_origin=raw_job.get("data_origin", "MANUAL"),
            normalization_version="v1",
            title_confidence=title_confidence,
            salary_confidence=salary_confidence,
            location_confidence=location_confidence,
            job_category=job_category,
            category_confidence=category_confidence
        )
        db.add(job)
        await db.flush()

        # 7. Save job skills with alias mapping
        skills = raw_job.get("skills", [])
        if skills:
            for skill_name in skills:
                skill_obj = await SkillService.get_or_create_skill(db, skill_name)
                job_skill = JobSkill(job_id=job.id, skill_name=skill_name, skill_id=skill_obj.id)
                db.add(job_skill)
            await db.flush()

        # 8. Run Cross-Source Deduplication checks
        await DeduplicationService.find_and_flag_duplicate(db, job)

        await db.commit()
        return job

    async def aggregate_jobs_from_remote_apis(self, db: AsyncSession) -> int:
        """Fetch jobs from RemoteOK, Arbeitnow, Greenhouse, and Lever public APIs"""
        # This acts as our jobs aggregator. In production, n8n calls this, or a celery worker executes it.
        # We will retrieve raw job items from API feeds. If feeds rate-limit or fail, we use a rich mock dataset
        # containing real-world software jobs to seed the PostgreSQL database for demonstration.
        count = 0
        jobs_to_ingest = []

        # Example Fetch 1: RemoteOK
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://remoteok.com/api")
                if res.status_code == 200:
                    data = res.json()
                    # First item is metadata, skip it
                    for item in data[1:15]:
                        jobs_to_ingest.append({
                            "title": item.get("position"),
                            "company_name": item.get("company"),
                            "description": item.get("description", ""),
                            "location": "Remote",
                            "job_type": "Full-time",
                            "is_remote": True,
                            "url": item.get("url"),
                            "company_logo": item.get("company_logo"),
                            "skills": item.get("tags", []),
                            "created_at": datetime.datetime.fromtimestamp(int(item.get("date", datetime.datetime.now().timestamp())), datetime.timezone.utc),
                            "data_origin": "REMOTE_OK"
                        })
        except Exception as e:
            print(f"Failed to fetch RemoteOK: {e}")

        # Example Fetch 2: Arbeitnow
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://www.arbeitnow.com/api/job-board-api")
                if res.status_code == 200:
                    data = res.json()
                    for item in data.get("data", [])[:15]:
                        jobs_to_ingest.append({
                            "title": item.get("title"),
                            "company_name": item.get("company_name"),
                            "description": item.get("description", ""),
                            "location": item.get("location", "Germany"),
                            "job_type": "Full-time" if "full-time" in item.get("job_types", []) else "Contract",
                            "is_remote": item.get("remote", False),
                            "url": item.get("url"),
                            "skills": item.get("tags", []),
                            "created_at": datetime.datetime.now(datetime.timezone.utc),
                            "data_origin": "ARBEITNOW"
                        })
        except Exception as e:
            print(f"Failed to fetch Arbeitnow: {e}")

        # Fallback/Seed Data only when in development/debug mode
        if settings.ENVIRONMENT == "development" or settings.DEBUG:
            from app.seed.development_jobs import DEV_SAMPLE_JOBS
            jobs_to_ingest.extend(DEV_SAMPLE_JOBS)

        for rj in jobs_to_ingest:
            try:
                j = await self.ingest_job(db, rj, "System Aggregator")
                if j:
                    count += 1
            except Exception as ex:
                await db.rollback()
                print(f"Failed to ingest job posting {rj.get('title')}: {ex}")

        return count

job_service = JobService()
