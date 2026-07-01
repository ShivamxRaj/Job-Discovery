from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.models import CleanupJob

class CleanupRepository(BaseRepository[CleanupJob]):
    def __init__(self):
        super().__init__(CleanupJob)

    async def create_job(self, db: AsyncSession, *, file_path: str) -> CleanupJob:
        """Register a new file cleanup job."""
        job = CleanupJob(
            file_path=file_path,
            status="PENDING",
            retry_count=0,
            max_retries=5,
        )
        db.add(job)
        await db.flush()
        return job

    async def get_pending_jobs(self, db: AsyncSession) -> List[CleanupJob]:
        """Fetch all cleanup jobs that are PENDING or FAILED and can be retried."""
        query = select(CleanupJob).where(
            CleanupJob.status.in_(["PENDING", "FAILED"]),
            CleanupJob.retry_count < CleanupJob.max_retries
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_success(self, db: AsyncSession, *, job_id: int) -> Optional[CleanupJob]:
        """Mark a cleanup job as successfully executed."""
        job = await self.get(db, job_id)
        if job:
            job.status = "SUCCESS"
            job.error_message = None
            db.add(job)
            await db.flush()
        return job

    async def mark_failed(self, db: AsyncSession, *, job_id: int, error_message: str) -> Optional[CleanupJob]:
        """Record a failure, increment retry count, and transition to permanent failure if needed."""
        job = await self.get(db, job_id)
        if job:
            job.retry_count += 1
            job.error_message = error_message
            if job.retry_count >= job.max_retries:
                job.status = "PERMANENT_FAILURE"
            else:
                job.status = "FAILED"
            db.add(job)
            await db.flush()
        return job

cleanup_repo = CleanupRepository()
