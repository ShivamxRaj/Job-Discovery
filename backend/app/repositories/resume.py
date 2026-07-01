from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.models import Resume, ResumeVersion, ResumeParsedData, ResumeSkill, ResumeEmbedding

class ResumeRepository(BaseRepository[Resume]):
    def __init__(self):
        super().__init__(Resume)

    async def get(self, db: AsyncSession, id: int) -> Optional[Resume]:
        from sqlalchemy.orm import selectinload
        query = (
            select(Resume)
            .where(Resume.id == id)
            .options(
                selectinload(Resume.versions).selectinload(ResumeVersion.parsed_data),
                selectinload(Resume.versions).selectinload(ResumeVersion.skills),
                selectinload(Resume.versions).selectinload(ResumeVersion.projects),
                selectinload(Resume.versions).selectinload(ResumeVersion.certifications),
                selectinload(Resume.versions).selectinload(ResumeVersion.embedding)
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(self, db: AsyncSession, user_id: int) -> List[Resume]:
        query = select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def add_version(
        self, db: AsyncSession, *, resume_id: int, version_number: int, file_path: str, file_hash: str
    ) -> ResumeVersion:
        version = ResumeVersion(
            resume_id=resume_id,
            version_number=version_number,
            file_path=file_path,
            file_hash=file_hash
        )
        db.add(version)
        await db.flush()
        return version

    async def get_latest_version(self, db: AsyncSession, resume_id: int) -> Optional[ResumeVersion]:
        from sqlalchemy.orm import selectinload
        query = (
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .options(
                selectinload(ResumeVersion.parsed_data),
                selectinload(ResumeVersion.skills),
                selectinload(ResumeVersion.projects),
                selectinload(ResumeVersion.certifications),
                selectinload(ResumeVersion.embedding)
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
                selectinload(ResumeVersion.parsed_data),
                selectinload(ResumeVersion.skills),
                selectinload(ResumeVersion.projects),
                selectinload(ResumeVersion.certifications),
                selectinload(ResumeVersion.embedding)
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def save_parsed_data(
        self, db: AsyncSession, *, version_id: int, raw_text: str, parsed_json: dict, quality_score: float, ats_score: float, suggestions: List[str]
    ) -> ResumeParsedData:
        parsed_data = ResumeParsedData(
            resume_version_id=version_id,
            raw_text=raw_text,
            parsed_json=parsed_json,
            quality_score=quality_score,
            ats_score=ats_score,
            suggestions=suggestions
        )
        db.add(parsed_data)
        await db.flush()
        return parsed_data

    async def save_skills(
        self, db: AsyncSession, *, version_id: int, skills: List[dict]
    ) -> List[ResumeSkill]:
        skill_objs = [
            ResumeSkill(resume_version_id=version_id, skill_name=s["name"], years_experience=s.get("years"))
            for s in skills
        ]
        db.add_all(skill_objs)
        await db.flush()
        return skill_objs

    async def save_embedding(
        self, db: AsyncSession, *, version_id: int, embedding: List[float]
    ) -> ResumeEmbedding:
        emb_obj = ResumeEmbedding(resume_version_id=version_id, embedding=embedding)
        db.add(emb_obj)
        await db.flush()
        return emb_obj

resume_repo = ResumeRepository()
