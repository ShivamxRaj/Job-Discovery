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
from app.services.ingestion_service import ingestion_service
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
    """Legacy trigger to ingest and index new jobs from feeds (calls all connectors)"""
    results = await ingestion_service.ingest_from_all_connectors(db)
    return {"message": "Ingestion triggered", "results": results}

@router.post("/ingestion/trigger", status_code=status.HTTP_200_OK)
async def trigger_raw_ingestion(
    limit_per_connector: int = 15,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger job ingestion from all connectors to populate the raw_jobs queue"""
    results = await ingestion_service.ingest_from_all_connectors(db, limit_per_connector)
    return {"message": "Raw ingestion triggered successfully", "results": results}

@router.get("/ingestion/health", status_code=status.HTTP_200_OK)
async def get_ingestion_health(
    current_user: User = Depends(get_current_user)
):
    """Check connection health for all job ingestion connectors"""
    health_status = await ingestion_service.check_connectors_health()
    return health_status

@router.post("/sync/{source}", status_code=status.HTTP_200_OK)
async def sync_connector_source(
    source: str,
    limit: int = 15,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync jobs from a specific source/connector directly into the raw_jobs staging queue"""
    try:
        summary = await ingestion_service.ingest_from_connector(db, source, limit)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")
