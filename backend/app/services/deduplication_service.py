import uuid
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Job, JobEmbedding
from app.core.config import settings

class DeduplicationService:
    @classmethod
    async def find_and_flag_duplicate(cls, db: AsyncSession, new_job: Job) -> bool:
        """
        Runs Tier 1: Strict Metadata Match at ingestion time before embeddings exist.
        Checks for jobs at the same company and city with the exact same normalized title within a 7-day window.
        """
        seven_days_ago = new_job.created_at - timedelta(days=7) if new_job.created_at else None
        
        query = select(Job).where(
            Job.company_id == new_job.company_id,
            Job.id != new_job.id
        )
        if seven_days_ago:
            query = query.where(Job.created_at >= seven_days_ago)
            
        res = await db.execute(query)
        candidates = res.scalars().all()
        
        for candidate in candidates:
            same_title = candidate.normalized_title.lower() == new_job.normalized_title.lower()
            same_city = (candidate.city or "").lower() == (new_job.city or "").lower()
            
            if same_title and same_city:
                group_id = candidate.duplicate_group_id or str(uuid.uuid4())
                if not candidate.duplicate_group_id:
                    candidate.duplicate_group_id = group_id
                    
                new_job.duplicate_group_id = group_id
                new_job.duplicate_reason = "STRICT_MATCH"
                new_job.duplicate_score = 1.0
                new_job.is_active = False  # Auto-merge
                
                await db.commit()
                return True
                
        return False

    @classmethod
    async def run_semantic_deduplication(cls, db: AsyncSession, job: Job) -> bool:
        """
        Runs Tier 2: Semantic Cosine Similarity on pgvector embeddings.
        Called asynchronously after the job embedding has been generated.
        """
        from app.repositories.job import job_repo
        
        # Get the job's embedding
        res = await db.execute(select(JobEmbedding).where(JobEmbedding.job_id == job.id))
        job_emb = res.scalar_one_or_none()
        if not job_emb:
            return False

        # Find closest embeddings (ordered by similarity)
        candidates = await job_repo.get_jobs_by_vector_similarity(
            db, embedding=job_emb.embedding, limit=5
        )
        
        for candidate, score in candidates:
            if candidate.id == job.id:
                continue
                
            # Filter matches above our semantic similarity threshold
            if score >= settings.DEDUP_SEMANTIC_THRESHOLD:
                # Group using a shared duplicate group UUID
                group_id = candidate.duplicate_group_id or str(uuid.uuid4())
                if not candidate.duplicate_group_id:
                    candidate.duplicate_group_id = group_id
                    
                job.duplicate_group_id = group_id
                job.duplicate_score = score
                
                if score >= settings.DEDUP_FUZZY_THRESHOLD_HIGH:
                    job.duplicate_reason = "FUZZY_MATCH_HIGH"
                    job.is_active = False  # Auto-merge high confidence
                elif score >= settings.DEDUP_FUZZY_THRESHOLD_MIN:
                    job.duplicate_reason = "FUZZY_MATCH_LOW_CONFIDENCE"
                    job.is_active = True   # Keep active for human audit
                else:
                    continue
                    
                await db.commit()
                return True
                
        return False
