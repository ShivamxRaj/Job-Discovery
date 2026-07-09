import asyncio
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.models import Job, JobEmbedding
from app.services.openai_service import openai_service
from app.repositories.job import job_repo

class EmbeddingService:
    """
    Manages asynchronous embedding generation queue for production jobs,
    handling API rate limits (429) gracefully without blocking ingestion.
    """

    async def process_pending_embeddings(self, db: AsyncSession, batch_size: int = 20) -> Dict[str, Any]:
        # 1. Fetch pending/failed jobs needing embeddings
        query = (
            select(Job)
            .where(Job.embedding_status.in_(["PENDING", "FAILED"]))
            .options(selectinload(Job.company))
            .limit(batch_size)
        )
        result = await db.execute(query)
        jobs = list(result.scalars().all())

        summary = {
            "attempted": len(jobs),
            "completed": 0,
            "failed": 0,
            "rate_limited": False
        }

        if not jobs:
            return summary

        # Pre-extract data to avoid lazy-loading or expiration issues during commits
        jobs_data = []
        for job in jobs:
            company_name = job.company.name if job.company else "Unknown Company"
            jobs_data.append({
                "id": job.id,
                "title": job.title,
                "company_name": company_name,
                "location": job.location,
                "description": job.description
            })

        for jd in jobs_data:
            job_id = jd["id"]
            text_to_embed = f"{jd['title']} at {jd['company_name']}. Location: {jd['location']}. Description: {jd['description']}"

            # Fetch fresh instance to update state
            job = await db.get(Job, job_id)
            if not job:
                continue

            # 2. Lock job in PROCESSING state
            job.embedding_status = "PROCESSING"
            await db.commit()

            try:
                # 3. Request OpenAI embedding vector (1536 dims)
                embedding = await openai_service.get_embedding(text_to_embed)

                # 4. Save embedding vector
                await job_repo.save_job_embedding(db, job_id=job_id, embedding=embedding)

                # 5. Mark as COMPLETED
                job = await db.get(Job, job_id)
                if job:
                    job.embedding_status = "COMPLETED"
                    job.embedding_error = None
                    await db.commit()
                    
                    from app.services.deduplication_service import DeduplicationService
                    await DeduplicationService.run_semantic_deduplication(db, job)
                summary["completed"] += 1

            except Exception as e:
                error_msg = str(e)
                # Check for rate limiting status (429)
                is_429 = "429" in error_msg or "ratelimit" in error_msg.lower()
                
                job = await db.get(Job, job_id)
                if job:
                    if is_429:
                        # Revert status to PENDING so it can be retried on next Celery run
                        job.embedding_status = "PENDING"
                        job.embedding_error = f"RateLimitReached: {error_msg}"
                    else:
                        # Permanent failure
                        job.embedding_status = "FAILED"
                        job.embedding_error = error_msg
                    await db.commit()

                if is_429:
                    summary["rate_limited"] = True
                    print(f"[Embedding Queue] Rate limit hit (429): {error_msg}. Job {job_id} reverted to PENDING. Aborting batch.")
                    break  # Stop processing the rest of this batch
                else:
                    summary["failed"] += 1
                    print(f"[Embedding Queue] Permanent error generating embedding for Job {job_id}: {error_msg}")

            # Sleep briefly between calls to avoid hitting minute rate limits
            await asyncio.sleep(0.5)

        return summary

    async def get_queue_metrics(self, db: AsyncSession) -> Dict[str, int]:
        """Expose queue health metrics (Pending, Processing, Completed, Failed counts)"""
        metrics = {
            "PENDING": 0,
            "PROCESSING": 0,
            "COMPLETED": 0,
            "FAILED": 0
        }
        res = await db.execute(text("SELECT embedding_status, COUNT(*) FROM jobs GROUP BY embedding_status"))
        for row in res.all():
            status, count = row[0], row[1]
            if status in metrics:
                metrics[status] = count
        return metrics

# Helper imports
from sqlalchemy import text

embedding_service = EmbeddingService()
