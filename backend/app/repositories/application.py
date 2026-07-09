from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.models import Application, JobRecommendation, Job
from app.core.config import settings

class ApplicationRepository(BaseRepository[Application]):
    def __init__(self):
        super().__init__(Application)

    async def get_by_user(self, db: AsyncSession, user_id: int) -> List[Application]:
        query = (
            select(Application)
            .where(Application.user_id == user_id)
            .options(
                selectinload(Application.job).selectinload(Job.company),
                selectinload(Application.job).selectinload(Job.skills)
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_recommendations_by_user(
        self, db: AsyncSession, user_id: int, resume_version_id: Optional[int] = None, limit: int = 10
    ) -> List[JobRecommendation]:
        query = (
            select(JobRecommendation)
            .join(Job, JobRecommendation.job_id == Job.id)
            .where(
                JobRecommendation.user_id == user_id,
                JobRecommendation.is_dismissed == False
            )
        )
        if resume_version_id is not None:
            query = query.where(JobRecommendation.resume_version_id == resume_version_id)
            
        from app.repositories.job import job_repo
        query = job_repo.apply_production_filter(query, include_seed=True)
            
        query = (
            query.order_by(JobRecommendation.score.desc())
            .limit(limit)
            .options(
                selectinload(JobRecommendation.job).selectinload(Job.company),
                selectinload(JobRecommendation.job).selectinload(Job.skills)
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def save_recommendations(
        self, db: AsyncSession, recs: List[dict]
    ) -> List[JobRecommendation]:
        objects = [JobRecommendation(**r) for r in recs]
        db.add_all(objects)
        await db.flush()

        # Re-fetch with eager loading so Pydantic can serialize nested relationships
        ids = [o.id for o in objects]
        query = (
            select(JobRecommendation)
            .where(JobRecommendation.id.in_(ids))
            .options(
                selectinload(JobRecommendation.job).selectinload(Job.company),
                selectinload(JobRecommendation.job).selectinload(Job.skills)
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_recommendation(
        self, db: AsyncSession, user_id: int, job_id: int, resume_version_id: Optional[int] = None
    ) -> Optional[JobRecommendation]:
        query = (
            select(JobRecommendation)
            .where(
                JobRecommendation.user_id == user_id,
                JobRecommendation.job_id == job_id
            )
        )
        if resume_version_id is not None:
            query = query.where(JobRecommendation.resume_version_id == resume_version_id)
            
        query = (
            query.order_by(JobRecommendation.created_at.desc())
            .options(
                selectinload(JobRecommendation.job).selectinload(Job.company),
                selectinload(JobRecommendation.job).selectinload(Job.skills)
            )
        )
        result = await db.execute(query)
        return result.scalars().first()

application_repo = ApplicationRepository()
