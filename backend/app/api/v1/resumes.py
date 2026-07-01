"""
Resume API — Phase 2B
----------------------
Endpoints:
  POST   /upload                       — upload + full intelligence pipeline
  GET    /                             — list user's resumes
  GET    /{resume_id}/versions         — list versions for a resume
  GET    /versions/{version_id}        — full parsed data + scores
  GET    /versions/{version_id}/analyze — re-run deterministic intelligence (no re-upload)
  GET    /versions/{version_id}/embedding — embedding verification report
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import (
    ResumeVersionResponse,
    ResumeResponse,
    EmbeddingMetadataResponse,
)
from app.services.resume_service import resume_service, EmbeddingVerification, EMBEDDING_MODEL
from app.repositories.resume import resume_repo
from app.core.resume_intelligence import run_intelligence

router = APIRouter()

ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt")


# ──────────────────────────────────────────────────────────────────────────────
# POST /upload
# ──────────────────────────────────────────────────────────────────────────────
@router.post(
    "/upload",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload resume",
    description=(
        "Upload a PDF, DOCX, or TXT resume. "
        "Triggers the full intelligence pipeline: AI parse → deterministic scoring "
        "(quality + ATS) → skill normalization → embedding generation. "
        "If the file cannot be text-extracted (scanned PDF), `ocr_status` is set to "
        "`PENDING_OCR` and scores will be `null` with an explicit reason."
    ),
    tags=["Resumes"],
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file"),
    title: str = Form("My Resume", description="Human-readable label for this resume"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    try:
        version = await resume_service.upload_and_parse_resume(
            db, user_id=current_user.id, file=file, title=title
        )
        return version
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume pipeline failed: {exc}",
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=List[ResumeResponse],
    summary="List resumes",
    tags=["Resumes"],
)
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all active resumes owned by the current user."""
    return await resume_repo.get_by_user(db, current_user.id)


# ──────────────────────────────────────────────────────────────────────────────
# GET /{resume_id}/versions
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/{resume_id}/versions",
    response_model=List[ResumeVersionResponse],
    summary="List resume versions",
    tags=["Resumes"],
)
async def list_resume_versions(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the full version history for a specific resume."""
    resume = await resume_repo.get(db, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume.versions


# ──────────────────────────────────────────────────────────────────────────────
# GET /versions/{version_id}
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/versions/{version_id}",
    response_model=ResumeVersionResponse,
    summary="Get resume version detail",
    description=(
        "Returns parsed data, deterministic quality/ATS scores, skill list, and OCR status. "
        "Scores may be `null` if the file is `PENDING_OCR` or parsed data is unavailable — "
        "check `quality_score_reason` / `ats_score_reason` for the explicit cause."
    ),
    tags=["Resumes"],
)
async def get_resume_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = await resume_repo.get_version(db, version_id)
    if not version or version.resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")
    return version


# ──────────────────────────────────────────────────────────────────────────────
# GET /versions/{version_id}/analyze
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/versions/{version_id}/analyze",
    response_model=ResumeVersionResponse,
    summary="Re-run intelligence analysis",
    description=(
        "Re-computes deterministic quality score, ATS score, skill normalization, "
        "and improvement suggestions from already-stored parsed data — without re-uploading. "
        "Useful after parser improvements or when recalibrating scores."
    ),
    tags=["Resume Intelligence"],
)
async def analyze_resume_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = await resume_repo.get_version(db, version_id)
    if not version or version.resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    if not version.parsed_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No parsed data available for this version. Re-upload the resume.",
        )

    parsed_json = version.parsed_data.parsed_json or {}
    raw_text = version.parsed_data.raw_text or ""
    intel = run_intelligence(parsed_json, raw_text)

    # Persist updated scores via ORM (works on both PostgreSQL and SQLite)
    pd = version.parsed_data
    pd.quality_score = intel.quality_score
    pd.quality_score_reason = intel.quality_score_reason
    pd.ats_score = intel.ats_score
    pd.ats_score_reason = intel.ats_score_reason
    pd.suggestions = intel.suggestions
    db.add(pd)
    await db.commit()

    return await resume_repo.get_version(db, version_id)


# ──────────────────────────────────────────────────────────────────────────────
# GET /versions/{version_id}/embedding
# ──────────────────────────────────────────────────────────────────────────────
@router.get(
    "/versions/{version_id}/embedding",
    response_model=EmbeddingMetadataResponse,
    summary="Embedding verification report",
    description=(
        "Returns embedding verification metadata: model name, vector dimensions, "
        "non-null check, non-zero check, and the first 5 sample values. "
        "Confirms the vector is correctly stored in pgvector."
    ),
    tags=["Resume Intelligence"],
)
async def get_embedding_verification(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = await resume_repo.get_version(db, version_id)
    if not version or version.resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    vector = await resume_repo.get_embedding_vector(db, version_id)
    if vector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No embedding found for this version. "
                "This may be a PENDING_OCR version or embedding generation failed."
            ),
        )

    ev = EmbeddingVerification(vector)
    pd = version.parsed_data

    return EmbeddingMetadataResponse(
        model=pd.embedding_model if pd and pd.embedding_model else EMBEDDING_MODEL,
        dimensions=pd.embedding_dimensions if pd and pd.embedding_dimensions else ev.dimensions,
        is_non_null=ev.is_non_null,
        is_non_zero=ev.is_non_zero,
        sample_values=ev.sample_values,
    )
