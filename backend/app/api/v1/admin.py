from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from sqlalchemy import select

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
    # Count totals
    from sqlalchemy import func
    
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    jobs_count = (await db.execute(select(func.count(Job.id)))).scalar() or 0
    apps_count = (await db.execute(select(func.count(Application.id)))).scalar() or 0
    resumes_count = (await db.execute(select(func.count(Resume.id)))).scalar() or 0
    
    return {
        "total_users": users_count,
        "total_jobs": jobs_count,
        "total_applications": apps_count,
        "total_resumes": resumes_count
    }
