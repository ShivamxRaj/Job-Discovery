"""
Resume Service — Phase 2B
--------------------------
Orchestrates the full resume intelligence pipeline:
  1. File hash + OCR/text extraction (with PENDING_OCR stub for binary-only PDFs)
  2. AI parsing via OpenAI (structured JSON)
  3. Deterministic scoring via IntelligenceEngine (no magic defaults)
  4. Skill normalization
  5. Embedding generation + verification (model, dimensions, non-null, non-zero)
  6. Transactional commit with storage rollback on failure (Phase 2A — untouched)
"""
from __future__ import annotations

import hashlib
import logging
from typing import Dict, Any, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.resume import resume_repo
from app.utils.parser import extract_resume_text
from app.utils.storage import storage_manager
from app.services.openai_service import openai_service
from app.core.resume_intelligence import run_intelligence
from app.models.models import ResumeVersion

logger = logging.getLogger(__name__)

# Embedding constants — single source of truth
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingVerification:
    """Holds embedding verification results for the API response."""
    __slots__ = ("model", "dimensions", "is_non_null", "is_non_zero", "sample_values")

    def __init__(self, vector: list):
        self.model = EMBEDDING_MODEL
        self.dimensions = len(vector)
        self.is_non_null = vector is not None and len(vector) > 0
        self.is_non_zero = any(v != 0.0 for v in vector) if vector else False
        self.sample_values = vector[:5] if vector else []

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "is_non_null": self.is_non_null,
            "is_non_zero": self.is_non_zero,
            "sample_values": self.sample_values,
        }


class ResumeService:
    async def upload_and_parse_resume(
        self, db: AsyncSession, user_id: int, file: UploadFile, title: str
    ) -> ResumeVersion:
        """
        Full pipeline:
        1. Read bytes + compute SHA-256 file hash
        2. Extract text (OCR stub if extraction yields < 50 chars)
        3. AI parse (structured JSON)
        4. Intelligence engine: deterministic quality/ATS scores, skill normalization, suggestions
        5. Save ResumeVersion, ParsedData, Skills, Embedding — all inside one DB transaction
        6. On any failure: db.rollback() + storage.delete_file() (Phase 2A guarantee)
        """
        # ── 1. Read file ──────────────────────────────────────────────────────
        content = await file.read()
        await file.seek(0)
        file_hash = hashlib.sha256(content).hexdigest()

        # ── 2. Text Extraction with OCR queue stub ────────────────────────────
        raw_text = await extract_resume_text(file)
        ocr_status = "READY"

        if len(raw_text.strip()) < 50:
            # Binary-only PDF (scanned image) — cannot extract text directly.
            # In production this would enqueue an OCR job (Celery/SQS).
            # For now we flag the version and return a stub so the DB is not left inconsistent.
            logger.warning(
                "File '%s' yielded < 50 chars of text. Flagging as PENDING_OCR.", file.filename
            )
            ocr_status = "PENDING_OCR"
            raw_text = ""  # no text to parse — intelligence will return null scores with reason

        # ── 3. Find or create Resume parent record ────────────────────────────
        resumes = await resume_repo.get_by_user(db, user_id)
        if resumes:
            resume = resumes[0]
            latest_ver = await resume_repo.get_latest_version(db, resume.id)
            version_number = (latest_ver.version_number + 1) if latest_ver else 1
        else:
            resume = await resume_repo.create(db, obj_in={"user_id": user_id, "title": title})
            version_number = 1

        uploaded_filename: Optional[str] = None

        try:
            # ── 4. Upload file to storage ─────────────────────────────────────
            unique_filename = f"resumes/{user_id}_{resume.id}_v{version_number}_{file.filename}"
            file_path = await storage_manager.upload_file(file, unique_filename)
            uploaded_filename = unique_filename

            # ── 5. Persist ResumeVersion (with ocr_status) ───────────────────
            version = await resume_repo.add_version(
                db,
                resume_id=resume.id,
                version_number=version_number,
                file_path=file_path,
                file_hash=file_hash,
                ocr_status=ocr_status,
            )

            # ── 6. AI Parse ───────────────────────────────────────────────────
            parsed_json: Dict[str, Any] = {}
            from app.services.openai_service import ParseFailedError, EmbeddingFailedError
            
            if ocr_status == "READY" and raw_text:
                try:
                    parsed_json = await openai_service.parse_resume(raw_text)
                except ParseFailedError as parse_err:
                    version.ocr_status = "PARSE_FAILED"
                    # Persist ParsedData with empty dict and error message suggestion
                    await resume_repo.save_parsed_data(
                        db,
                        version_id=version.id,
                        raw_text=raw_text,
                        parsed_json={},
                        quality_score=None,
                        quality_score_reason="Parsing failed",
                        ats_score=None,
                        ats_score_reason="Parsing failed",
                        suggestions=["Resume parsing failed. Retrying..."],
                    )
                    await db.commit()
                    
                    # Queue retry
                    try:
                        from app.services.celery_app import retry_failed_resume_task
                        retry_failed_resume_task.delay(version.id)
                    except Exception as celery_err:
                        logger.warning("Failed to queue Celery retry for resume %d: %s", version.id, celery_err)
                    
                    raise parse_err

            # ── 7. Intelligence Engine (deterministic) ────────────────────────
            intel = run_intelligence(parsed_json, raw_text)

            # ── 8. Persist ParsedData (null scores explicitly stored) ─────────
            await resume_repo.save_parsed_data(
                db,
                version_id=version.id,
                raw_text=raw_text,
                parsed_json=parsed_json,
                quality_score=intel.quality_score,
                quality_score_reason=intel.quality_score_reason,
                ats_score=intel.ats_score,
                ats_score_reason=intel.ats_score_reason,
                suggestions=intel.suggestions,
            )

            # ── 9. Persist Normalized Skills ──────────────────────────────────
            await resume_repo.save_skills(
                db, version_id=version.id, skills=intel.normalized_skills
            )

            # ── 10. Generate Embedding + Verify ──────────────────────────────
            embedding_vector: list = []
            embedding_verify: Optional[EmbeddingVerification] = None

            if ocr_status == "READY" and raw_text:
                try:
                    embedding_vector = await openai_service.get_embedding(raw_text)
                except EmbeddingFailedError as emb_err:
                    version.ocr_status = "EMBEDDING_FAILED"
                    await db.commit()
                    
                    # Queue retry
                    try:
                        from app.services.celery_app import retry_failed_resume_task
                        retry_failed_resume_task.delay(version.id)
                    except Exception as celery_err:
                        logger.warning("Failed to queue Celery retry for resume %d: %s", version.id, celery_err)
                        
                    raise emb_err
                    
                embedding_verify = EmbeddingVerification(embedding_vector)

                # Validation assertions before storing
                if not embedding_verify.is_non_null:
                    raise ValueError(
                        f"Embedding returned null/empty for version {version.id}"
                    )
                if embedding_verify.dimensions != EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, "
                        f"got {embedding_verify.dimensions}"
                    )
                if not embedding_verify.is_non_zero:
                    logger.warning("Embedding vector is all zeros for version %d", version.id)

                await resume_repo.save_embedding(
                    db, version_id=version.id, embedding=embedding_vector
                )

                # Store embedding metadata in parsed_data row
                await resume_repo.update_embedding_metadata(
                    db,
                    version_id=version.id,
                    model=EMBEDDING_MODEL,
                    dimensions=embedding_verify.dimensions,
                )

                logger.info(
                    "Embedding verified: model=%s dims=%d non_null=%s non_zero=%s",
                    embedding_verify.model,
                    embedding_verify.dimensions,
                    embedding_verify.is_non_null,
                    embedding_verify.is_non_zero,
                )

            # ── 11. Commit ────────────────────────────────────────────────────
            await db.commit()

            return await resume_repo.get_version(db, version.id)

        except (ParseFailedError, EmbeddingFailedError) as ai_err:
            # Let these flow up directly without invoking file cleanup since the version metadata is preserved
            raise ai_err
        except Exception as exc:
            await db.rollback()
            if uploaded_filename:
                try:
                    from app.repositories.cleanup import cleanup_repo
                    # Create and persist a new cleanup job to the database
                    job = await cleanup_repo.create_job(db, file_path=uploaded_filename)
                    await db.commit()
                    
                    # Trigger the async deletion task immediately in the background
                    try:
                        from app.services.celery_app import delete_storage_file_task
                        delete_storage_file_task.delay(job.id)
                    except Exception as celery_err:
                        logger.warning(
                            "Failed to enqueue celery task for cleanup job %d: %s. Will fall back to scheduled cron.",
                            job.id, celery_err
                        )
                except Exception as cleanup_db_err:
                    logger.error(
                        "Failed to register CleanupJob for file '%s': %s",
                        uploaded_filename, cleanup_db_err
                    )
            raise exc

    async def retry_failed_stages(self, db: AsyncSession, version_id: int) -> Optional[ResumeVersion]:
        """Retry parsing or embedding generation for a previously failed resume version."""
        version = await resume_repo.get_version(db, version_id)
        if not version:
            return None
            
        from app.services.openai_service import ParseFailedError, EmbeddingFailedError
        
        # If parsing failed, retry parsing and embedding
        if version.ocr_status == "PARSE_FAILED":
            raw_text = version.parsed_data.raw_text if version.parsed_data else ""
            if not raw_text:
                return version
            try:
                parsed_json = await openai_service.parse_resume(raw_text)
                intel = run_intelligence(parsed_json, raw_text)
                
                await resume_repo.save_parsed_data(
                    db,
                    version_id=version.id,
                    raw_text=raw_text,
                    parsed_json=parsed_json,
                    quality_score=intel.quality_score,
                    quality_score_reason=intel.quality_score_reason,
                    ats_score=intel.ats_score,
                    ats_score_reason=intel.ats_score_reason,
                    suggestions=intel.suggestions,
                )
                
                await resume_repo.save_skills(
                    db, version_id=version.id, skills=intel.normalized_skills
                )
                
                embedding_vector = await openai_service.get_embedding(raw_text)
                await resume_repo.save_embedding(db, version_id=version.id, embedding=embedding_vector)
                
                await resume_repo.update_embedding_metadata(
                    db,
                    version_id=version.id,
                    model=EMBEDDING_MODEL,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                
                version.ocr_status = "READY"
                await db.commit()
            except ParseFailedError:
                pass
            except EmbeddingFailedError:
                version.ocr_status = "EMBEDDING_FAILED"
                await db.commit()
                
        # If only embedding failed, retry embedding
        elif version.ocr_status == "EMBEDDING_FAILED":
            raw_text = version.parsed_data.raw_text if version.parsed_data else ""
            if not raw_text:
                return version
            try:
                embedding_vector = await openai_service.get_embedding(raw_text)
                await resume_repo.save_embedding(db, version_id=version.id, embedding=embedding_vector)
                
                await resume_repo.update_embedding_metadata(
                    db,
                    version_id=version.id,
                    model=EMBEDDING_MODEL,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                
                version.ocr_status = "READY"
                await db.commit()
            except EmbeddingFailedError:
                pass
                
        return version


resume_service = ResumeService()
