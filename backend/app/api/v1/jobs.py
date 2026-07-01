from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.models import User, JobRecommendation, Job
from app.schemas.schemas import JobRecommendationResponse, JobResponse
from app.services.matching_service import matching_service
from app.services.job_service import job_service
from app.repositories.resume import resume_repo
from app.repositories.application import application_repo

router = APIRouter()

@router.get("/recommendations", response_model=List[JobRecommendationResponse])
async def get_job_recommendations(
    resume_version_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve top AI matches. Triggers matching engine if no recommendations cached."""
    # Find resume version
    version_id = resume_version_id
    if not version_id:
        resumes = await resume_repo.get_by_user(db, current_user.id)
        if not resumes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload a resume first to get recommendations."
            )
        latest_ver = await resume_repo.get_latest_version(db, resumes[0].id)
        if not latest_ver:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume contains no parsed version history."
            )
        version_id = latest_ver.id

    # Check database cache first
    recs = await application_repo.get_recommendations_by_user(db, current_user.id)
    if not recs:
        # Run matching pipeline
        recs = await matching_service.match_resume_to_jobs(db, current_user.id, version_id)
        
    return recs

@router.post("/recommendations/{job_id}/save", response_model=JobRecommendationResponse)
async def save_recommendation(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save/bookmark a recommended job"""
    rec = await application_repo.get_recommendation(db, current_user.id, job_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    
    rec.is_saved = True
    await db.commit()
    return rec

@router.post("/recommendations/{job_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_recommendation(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dismiss/hide a recommended job"""
    rec = await application_repo.get_recommendation(db, current_user.id, job_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    
    rec.is_dismissed = True
    await db.commit()
    return

@router.get("", response_model=List[JobResponse])
async def search_all_jobs(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Fetch/Search general job listings"""
    query = select(Job).where(Job.is_active == True)
    if search:
        query = query.where(Job.title.ilike(f"%{search}%") | Job.description.ilike(f"%{search}%"))
    
    # Load relationships
    from sqlalchemy.orm import selectinload
    query = query.options(selectinload(Job.company), selectinload(Job.skills)).limit(20)
    result = await db.execute(query)
    return list(result.scalars().all())

@router.post("/trigger-ingestion", status_code=status.HTTP_200_OK)
async def trigger_job_ingestion(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin/User trigger to ingest and index new jobs from feeds"""
    count = await job_service.aggregate_jobs_from_remote_apis(db)
    return {"message": f"Successfully ingested {count} jobs"}
