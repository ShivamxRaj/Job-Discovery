from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import ResumeVersionResponse, ResumeResponse
from app.services.resume_service import resume_service
from app.repositories.resume import resume_repo

router = APIRouter()

@router.post("/upload", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    title: str = Form("My Resume"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload resume PDF/DOCX, parse text, generate scores & embeddings"""
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF, DOCX, and TXT files are supported."
        )
    
    try:
        version = await resume_service.upload_and_parse_resume(
            db, user_id=current_user.id, file=file, title=title
        )
        return version
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while uploading and parsing: {str(e)}"
        )

@router.get("", response_model=List[ResumeResponse])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all resumes uploaded by user"""
    resumes = await resume_repo.get_by_user(db, current_user.id)
    return resumes

@router.get("/{resume_id}/versions", response_model=List[ResumeVersionResponse])
async def list_resume_versions(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete version history for a specific resume"""
    resume = await resume_repo.get(db, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    return resume.versions

@router.get("/versions/{version_id}", response_model=ResumeVersionResponse)
async def get_resume_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch parsed data and scores for a specific version ID"""
    version = await resume_repo.get_version(db, version_id)
    if not version or version.resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found"
        )
    return version
