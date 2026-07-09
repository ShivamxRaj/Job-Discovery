from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.models import Job, JobEmbedding, JobSkill, Company, JobSource, DuplicateGroup
from app.core.config import settings

class JobRepository(BaseRepository[Job]):
    def __init__(self):
        super().__init__(Job)

    @staticmethod
    def apply_production_filter(query, include_seed: bool = False):
        """
        Applies is_seed_data filtering to an existing SQLAlchemy query.
        Production is the default path (excludes seed jobs).
        Development/debug must explicitly opt-in by setting include_seed=True.
        """
        if include_seed and (settings.ENVIRONMENT == "development" or settings.DEBUG):
            return query
        return query.where(Job.is_seed_data == False)

    async def get_by_url(self, db: AsyncSession, url: str) -> Optional[Job]:
        query = select(Job).where(Job.url == url)
        query = self.apply_production_filter(query, include_seed=True)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_company_by_name(self, db: AsyncSession, name: str) -> Optional[Company]:
        normalized = name.strip().lower()
        query = select(Company).where(Company.normalized_name == normalized)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_company(self, db: AsyncSession, *, name: str, normalized_name: str, industry: Optional[str] = None, website: Optional[str] = None, logo_url: Optional[str] = None) -> Company:
        company = Company(
            name=name,
            normalized_name=normalized_name,
            industry=industry,
            website=website,
            logo_url=logo_url
        )
        db.add(company)
        await db.flush()
        return company

    async def get_source_by_name(self, db: AsyncSession, name: str) -> Optional[JobSource]:
        query = select(JobSource).where(JobSource.name == name)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_jobs_by_vector_similarity(
        self, db: AsyncSession, embedding: List[float], limit: int = 100
    ) -> List[Tuple[Job, float]]:
        # Check if using SQLite
        if db.bind.dialect.name == "sqlite":
            import math
            import json
            
            # Retrieve all job embeddings
            query = (
                select(Job, JobEmbedding)
                .join(JobEmbedding, Job.id == JobEmbedding.job_id)
                .where(and_(Job.is_active == True, Job.embedding_status == 'COMPLETED'))
            )
            query = self.apply_production_filter(query, include_seed=True)
            
            query = query.options(selectinload(Job.company), selectinload(Job.skills))
            result = await db.execute(query)
            rows = result.all()
            
            def cosine_similarity(v1, v2):
                if v1 is None or v2 is None or len(v1) == 0 or len(v2) == 0:
                    return 0.0
                dot_prod = sum(x * y for x, y in zip(v1, v2))
                mag1 = math.sqrt(sum(x * x for x in v1))
                mag2 = math.sqrt(sum(x * x for x in v2))
                if mag1 * mag2 == 0:
                    return 0.0
                return dot_prod / (mag1 * mag2)
            
            jobs_with_scores = []
            for job, job_emb in rows:
                emb_list = job_emb.embedding
                if isinstance(emb_list, str):
                    try:
                        emb_list = json.loads(emb_list)
                    except Exception:
                        emb_list = []
                # Compute similarity
                score = cosine_similarity(embedding, emb_list)
                jobs_with_scores.append((job, score))
            
            # Sort descending and limit
            jobs_with_scores.sort(key=lambda x: x[1], reverse=True)
            return jobs_with_scores[:limit]

        # pgvector cosine_distance returns value between 0 (identical) and 2 (orthogonal/opposite).
        # Cosine similarity = 1 - cosine_distance.
        distance_expr = JobEmbedding.embedding.cosine_distance(embedding)
        query = (
            select(Job, (1.0 - distance_expr).label("similarity"))
            .join(JobEmbedding, Job.id == JobEmbedding.job_id)
            .where(and_(Job.is_active == True, Job.embedding_status == 'COMPLETED'))
        )
        query = self.apply_production_filter(query, include_seed=True)
            
        query = (
            query.order_by(distance_expr)
            .limit(limit)
            .options(selectinload(Job.company), selectinload(Job.skills))
        )
        result = await db.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def save_job_embedding(self, db: AsyncSession, *, job_id: int, embedding: List[float]) -> JobEmbedding:
        emb_obj = JobEmbedding(job_id=job_id, embedding=embedding)
        db.add(emb_obj)
        await db.flush()
        return emb_obj

    async def save_job_skills(self, db: AsyncSession, *, job_id: int, skills: List[str]) -> List[JobSkill]:
        skill_objs = [JobSkill(job_id=job_id, skill_name=s) for s in skills]
        db.add_all(skill_objs)
        await db.flush()
        return skill_objs

    async def add_duplicate_relation(self, db: AsyncSession, *, primary_id: int, duplicate_id: int, score: float) -> DuplicateGroup:
        rel = DuplicateGroup(primary_job_id=primary_id, duplicate_job_id=duplicate_id, similarity_score=score)
        db.add(rel)
        await db.flush()
        return rel

job_repo = JobRepository()
