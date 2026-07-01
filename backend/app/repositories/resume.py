from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.models import Resume, ResumeVersion, ResumeParsedData, ResumeSkill, ResumeEmbedding


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self):
        super().__init__(Resume)

    # ------------------------------------------------------------------
    # Resume queries
    # ------------------------------------------------------------------

    async def get(self, db: AsyncSession, id: int) -> Optional[Resume]:
        query = (
            select(Resume)
            .where(Resume.id == id)
            .options(
                selectinload(Resume.versions).selectinload(ResumeVersion.parsed_data),
                selectinload(Resume.versions).selectinload(ResumeVersion.skills),
                selectinload(Resume.versions).selectinload(ResumeVersion.projects),
                selectinload(Resume.versions).selectinload(ResumeVersion.certifications),
                selectinload(Resume.versions).selectinload(ResumeVersion.embedding),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(self, db: AsyncSession, user_id: int) -> List[Resume]:
        query = select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Version helpers
    # ------------------------------------------------------------------

    async def add_version(
        self,
        db: AsyncSession,
        *,
        resume_id: int,
        version_number: int,
        file_path: str,
        file_hash: str,
        ocr_status: str = "READY",
    ) -> ResumeVersion:
        version = ResumeVersion(
            resume_id=resume_id,
            version_number=version_number,
            file_path=file_path,
            file_hash=file_hash,
            ocr_status=ocr_status,
        )
        db.add(version)
        await db.flush()
        return version

    async def get_latest_version(self, db: AsyncSession, resume_id: int) -> Optional[ResumeVersion]:
        query = (
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .options(
                selectinload(ResumeVersion.parsed_data),
                selectinload(ResumeVersion.skills),
                selectinload(ResumeVersion.projects),
                selectinload(ResumeVersion.certifications),
                selectinload(ResumeVersion.embedding),
            )
            .order_by(ResumeVersion.version_number.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_version(self, db: AsyncSession, version_id: int) -> Optional[ResumeVersion]:
        from sqlalchemy.orm import selectinload
        query = (
            select(ResumeVersion)
            .where(ResumeVersion.id == version_id)
            .options(
                selectinload(ResumeVersion.resume),
                selectinload(ResumeVersion.parsed_data),
                selectinload(ResumeVersion.skills),
                selectinload(ResumeVersion.projects),
                selectinload(ResumeVersion.certifications),
                selectinload(ResumeVersion.embedding),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_version_with_embedding(
        self, db: AsyncSession, version_id: int
    ) -> Optional[ResumeVersion]:
        """Same as get_version but always eager-loads embedding relationship."""
        return await self.get_version(db, version_id)

    # ------------------------------------------------------------------
    # Parsed data persistence
    # ------------------------------------------------------------------

    async def save_parsed_data(
        self,
        db: AsyncSession,
        *,
        version_id: int,
        raw_text: str,
        parsed_json: Dict[str, Any],
        quality_score: Optional[float],
        quality_score_reason: Optional[str] = None,
        ats_score: Optional[float],
        ats_score_reason: Optional[str] = None,
        suggestions: Optional[List[str]],
    ) -> ResumeParsedData:
        parsed_data = ResumeParsedData(
            resume_version_id=version_id,
            raw_text=raw_text,
            parsed_json=parsed_json,
            quality_score=quality_score,
            quality_score_reason=quality_score_reason,
            ats_score=ats_score,
            ats_score_reason=ats_score_reason,
            suggestions=suggestions or [],
        )
        db.add(parsed_data)
        await db.flush()
        return parsed_data

    async def update_embedding_metadata(
        self,
        db: AsyncSession,
        *,
        version_id: int,
        model: str,
        dimensions: int,
    ) -> None:
        """Persist embedding model name and dimension count into parsed_data row."""
        query = select(ResumeParsedData).where(
            ResumeParsedData.resume_version_id == version_id
        )
        result = await db.execute(query)
        pd = result.scalar_one_or_none()
        if pd:
            pd.embedding_model = model
            pd.embedding_dimensions = dimensions
            db.add(pd)

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    async def save_skills(
        self, db: AsyncSession, *, version_id: int, skills: List[Dict[str, Any]]
    ) -> List[ResumeSkill]:
        skill_objs = [
            ResumeSkill(
                resume_version_id=version_id,
                skill_name=s["name"],
                years_experience=s.get("years_experience"),
            )
            for s in skills
        ]
        db.add_all(skill_objs)
        await db.flush()
        return skill_objs

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def save_embedding(
        self, db: AsyncSession, *, version_id: int, embedding: List[float]
    ) -> ResumeEmbedding:
        emb_obj = ResumeEmbedding(resume_version_id=version_id, embedding=embedding)
        db.add(emb_obj)
        await db.flush()
        return emb_obj

    async def get_embedding_vector(
        self, db: AsyncSession, version_id: int
    ) -> Optional[list]:
        """
        Return raw embedding vector by loading from the eager-loaded
        ResumeVersion.embedding relationship (avoids MissingGreenlet on SQLite).
        """
        version = await self.get_version(db, version_id)
        if version is None or version.embedding is None:
            return None
        vec = version.embedding.embedding
        return list(vec) if vec is not None else None


resume_repo = ResumeRepository()
