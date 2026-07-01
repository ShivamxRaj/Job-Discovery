from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import User, Application
from app.schemas.schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse, CoverLetterGenerateRequest, AICoverLetterResponse, AIHREmailResponse
from app.repositories.application import application_repo
from app.repositories.job import job_repo
from app.repositories.resume import resume_repo
from app.services.openai_service import openai_service

router = APIRouter()

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    app_in: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Log a job application for tracking"""
    # Verify job and resume version belong to valid records
    job = await job_repo.get(db, app_in.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")
        
    version = await resume_repo.get_version(db, app_in.resume_version_id)
    if not version or version.resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    app_dict = {
        "user_id": current_user.id,
        "job_id": app_in.job_id,
        "resume_version_id": app_in.resume_version_id,
        "status": app_in.status,
        "notes": app_in.notes
    }
    app = await application_repo.create(db, obj_in=app_dict)
    await db.commit()
    
    # Reload application details
    apps = await application_repo.get_by_user(db, current_user.id)
    ret_app = next((a for a in apps if a.id == app.id), app)
    return ret_app

@router.get("", response_model=List[ApplicationResponse])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all tracked job applications"""
    apps = await application_repo.get_by_user(db, current_user.id)
    return apps

@router.put("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: int,
    app_update: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update status or notes for an application"""
    app = await application_repo.get(db, app_id)
    if not app or app.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application tracker not found")

    app = await application_repo.update(db, db_obj=app, obj_in=app_update.model_dump(exclude_unset=True))
    await db.commit()
    
    apps = await application_repo.get_by_user(db, current_user.id)
    ret_app = next((a for a in apps if a.id == app.id), app)
    return ret_app

@router.post("/generate-cover-letter", response_model=AICoverLetterResponse)
async def generate_cover_letter(
    req: CoverLetterGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a custom cover letter tailormade for a job and resume"""
    job = await job_repo.get(db, req.job_id)
    version = await resume_repo.get_version(db, req.resume_version_id)
    
    if not job or not version or version.resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job or resume version not found")

    raw_text = version.parsed_data.raw_text if version.parsed_data else "Candidate Resume Content"
    job_desc = job.description
    
    cover_letter = await openai_service.generate_cover_letter(raw_text, job_desc)
    return AICoverLetterResponse(cover_letter=cover_letter)

@router.post("/generate-hr-email", response_model=AIHREmailResponse)
async def generate_hr_email(
    req: CoverLetterGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate cold outreach recruiter email customized to a job and resume"""
    job = await job_repo.get(db, req.job_id)
    version = await resume_repo.get_version(db, req.resume_version_id)
    
    if not job or not version or version.resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job or resume version not found")

    raw_text = version.parsed_data.raw_text if version.parsed_data else "Candidate Resume Content"
    job_desc = job.description
    
    hr_email = await openai_service.generate_hr_email(raw_text, job_desc)
    return AIHREmailResponse(hr_email=hr_email)
