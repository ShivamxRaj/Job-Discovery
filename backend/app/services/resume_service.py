import hashlib
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.resume import resume_repo
from app.utils.parser import extract_resume_text
from app.utils.storage import storage_manager
from app.services.openai_service import openai_service
from app.models.models import Resume, ResumeVersion

class ResumeService:
    async def upload_and_parse_resume(
        self, db: AsyncSession, user_id: int, file: UploadFile, title: str
    ) -> ResumeVersion:
        # 1. Read file bytes and calculate hash (to detect duplicate uploads)
        content = await file.read()
        await file.seek(0)
        file_hash = hashlib.sha256(content).hexdigest()

        # 2. Extract raw text from resume (PDF/DOCX)
        raw_text = await extract_resume_text(file)

        # 3. Create or find active Resume record
        # For simplicity, we create a new resume, or append a version if resume exists
        # In a real SaaS, we can group under the same resume
        resumes = await resume_repo.get_by_user(db, user_id)
        if resumes:
            resume = resumes[0]
            latest_ver = await resume_repo.get_latest_version(db, resume.id)
            version_number = (latest_ver.version_number + 1) if latest_ver else 1
        else:
            resume = await resume_repo.create(db, obj_in={"user_id": user_id, "title": title})
            version_number = 1

        # 4. Upload file to storage
        unique_filename = f"resumes/{user_id}_{resume.id}_v{version_number}_{file.filename}"
        file_path = await storage_manager.upload_file(file, unique_filename)

        # 5. Add Resume Version record
        version = await resume_repo.add_version(
            db,
            resume_id=resume.id,
            version_number=version_number,
            file_path=file_path,
            file_hash=file_hash
        )

        # 6. Parse resume text via OpenAI
        parsed_data = await openai_service.parse_resume(raw_text)

        # 7. Save parsed JSON profile data, scores and recommendations suggestions
        await resume_repo.save_parsed_data(
            db,
            version_id=version.id,
            raw_text=raw_text,
            parsed_json=parsed_data,
            quality_score=parsed_data.get("quality_score", 70.0),
            ats_score=parsed_data.get("ats_score", 70.0),
            suggestions=parsed_data.get("suggestions", [])
        )

        # 8. Save structured skills
        skills = parsed_data.get("skills", [])
        # skills might be a list of strings or list of dicts. Standardize to list of dicts:
        formatted_skills = []
        for s in skills:
            if isinstance(s, str):
                formatted_skills.append({"name": s, "years": None})
            elif isinstance(s, dict):
                formatted_skills.append({"name": s.get("name", "Unknown"), "years": s.get("years")})
        await resume_repo.save_skills(db, version_id=version.id, skills=formatted_skills)

        # 9. Generate and save embedding vector
        embedding = await openai_service.get_embedding(raw_text)
        await resume_repo.save_embedding(db, version_id=version.id, embedding=embedding)

        # Commit all DB operations
        await db.commit()
        
        # Reload version to include relationships
        return await resume_repo.get_version(db, version.id)

resume_service = ResumeService()
