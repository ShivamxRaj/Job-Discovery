from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from sqlalchemy import select, text, func

from app.db.session import get_db
from app.core.security import get_current_active_superuser
from app.models.models import User, AuditLog, Job, Application, Resume
from app.schemas.schemas import UserResponse

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_superuser)
):
    """Retrieve list of registered users (Admin Only)"""
    query = select(User).order_by(User.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())

@router.get("/audit-logs", response_model=List[Dict[str, Any]])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_superuser)
):
    """Fetch system audit log trail (Admin Only)"""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details,
            "created_at": log.created_at
        } for log in logs
    ]

@router.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_superuser)
):
    """Fetch administrative analytics details (Admin Only)"""
    from app.core.config import settings
    
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    
    jobs_query = select(func.count(Job.id))
    from app.repositories.job import job_repo
    jobs_query = job_repo.apply_production_filter(jobs_query, include_seed=True)
    jobs_count = (await db.execute(jobs_query)).scalar() or 0
    
    apps_count = (await db.execute(select(func.count(Application.id)))).scalar() or 0
    resumes_count = (await db.execute(select(func.count(Resume.id)))).scalar() or 0
    
    return {
        "total_users": users_count,
        "total_jobs": jobs_count,
        "total_applications": apps_count,
        "total_resumes": resumes_count
    }


@router.get("/queue-health", response_model=Dict[str, Any])
async def get_embedding_queue_health(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_active_superuser)
):
    """
    Embedding queue health dashboard.
    
    Returns real-time metrics about the embedding pipeline status.
    
    TD-006 Status: Known Operational Limitation.
    Provider: GitHub Models (text-embedding-3-small).
    Limit: 150 requests/day (free tier). Scheduled: daily at 00:05 UTC.
    """
    # Status distribution
    status_res = await db.execute(text(
        "SELECT embedding_status, COUNT(*) FROM jobs GROUP BY embedding_status;"
    ))
    status_counts = {row[0]: row[1] for row in status_res.all()}

    pending = status_counts.get("PENDING", 0)
    completed = status_counts.get("COMPLETED", 0)
    processing = status_counts.get("PROCESSING", 0)
    failed = status_counts.get("FAILED", 0)
    total = pending + completed + processing + failed

    # Oldest pending job
    oldest_res = await db.execute(text(
        """SELECT id, title, created_at, NOW() - created_at as age 
           FROM jobs WHERE embedding_status = 'PENDING' 
           ORDER BY created_at ASC LIMIT 1;"""
    ))
    oldest_row = oldest_res.first()
    oldest_pending = None
    if oldest_row:
        oldest_pending = {
            "job_id": oldest_row[0],
            "title": oldest_row[1],
            "created_at": str(oldest_row[2]),
            "age": str(oldest_row[3])
        }

    # Coverage percentage
    coverage_pct = round((completed / total * 100), 1) if total > 0 else 0.0

    return {
        # Status counts
        "pending": pending,
        "completed": completed,
        "processing": processing,
        "failed": failed,
        "total_jobs": total,
        # Health indicators
        "coverage_pct": coverage_pct,
        "oldest_pending_job": oldest_pending,
        # Operational metadata (TD-006)
        "provider": "GitHub Models",
        "model": "text-embedding-3-small",
        "daily_quota": 150,
        "td_006_status": "Known Operational Limitation",
        "scheduler": "Celery Beat — daily at 00:05 UTC",
        "scheduler_task": "tasks.process_job_embeddings_daily",
        "note": (
            "Provider is GitHub Models free tier (150 req/day). "
            "Pending jobs are cleared automatically at 00:05 UTC daily. "
            "Migrate to paid provider when user volume justifies cost."
        )
    }
