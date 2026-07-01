from celery import Celery
from celery.schedules import crontab
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select

from app.core.config import settings

celery = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Register Dynamic Celery Beat Schedule based on Env Configs
celery.conf.beat_schedule = {
    "send-daily-digest-at-8am": {
        "task": "tasks.send_daily_digest",
        "schedule": crontab(
            hour=settings.DAILY_DIGEST_HOUR,
            minute=settings.DAILY_DIGEST_MINUTE
        ),
    },
    "send-weekly-digest-on-monday-8am": {
        "task": "tasks.send_weekly_digest",
        "schedule": crontab(
            hour=settings.WEEKLY_DIGEST_HOUR,
            minute=settings.WEEKLY_DIGEST_MINUTE,
            day_of_week=settings.WEEKLY_DIGEST_DAY_OF_WEEK
        ),
    },
}

# Helper to run async db queries within Celery sync threads
def run_async_task(coro):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def build_and_send_digest_email(db, user, digest_type: str):
    from app.repositories.resume import resume_repo
    from app.services.matching_service import matching_service
    
    resumes = await resume_repo.get_by_user(db, user.id)
    if not resumes:
        return False
    latest_ver = await resume_repo.get_latest_version(db, resumes[0].id)
    if not latest_ver:
        return False
        
    recs = await matching_service.match_resume_to_jobs(db, user.id, latest_ver.id)
    if not recs:
        return False
        
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg['To'] = user.email
            msg['Subject'] = f"Your {digest_type} AI Job Recommendations Digest"
            
            html = f"<h3>Hello! Here are your top job recommendations for this {digest_type.lower()}:</h3><ul>"
            for rec in recs[:5]:
                html += f"<li><strong>{rec.job.title}</strong> at {rec.job.company.name} (Score: {rec.score}%)<br/>"
                html += f"<em>{rec.explanation}</em><br/>"
                html += f"<a href='{rec.job.url}'>View Job Listing</a></li><br/>"
            html += "</ul><p>Login to your dashboard to view more recommendations.</p>"
            
            msg.attach(MIMEText(html, 'html'))
            
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, user.email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send email to {user.email}: {e}")
    return False

@celery.task(name="tasks.aggregate_jobs")
def aggregate_jobs_task():
    """Background task to fetch and normalize jobs"""
    from app.db.session import async_session_maker
    from app.services.job_service import job_service
    
    async def run():
        async with async_session_maker() as db:
            count = await job_service.aggregate_jobs_from_remote_apis(db)
            return f"Successfully ingested {count} jobs."
    return run_async_task(run())

@celery.task(name="tasks.send_daily_digest")
def send_daily_digest_task():
    """Background task to send daily job recommendations email digest"""
    from app.db.session import async_session_maker
    from app.models.models import User
    
    async def run():
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()
            
            emails_sent = 0
            for user in users:
                sent = await build_and_send_digest_email(db, user, "Daily")
                if sent:
                    emails_sent += 1
            return f"Sent daily digest to {emails_sent} users."
    return run_async_task(run())

@celery.task(name="tasks.send_weekly_digest")
def send_weekly_digest_task():
    """Background task to send weekly job recommendations email digest"""
    from app.db.session import async_session_maker
    from app.models.models import User
    
    async def run():
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.is_active == True))
            users = result.scalars().all()
            
            emails_sent = 0
            for user in users:
                sent = await build_and_send_digest_email(db, user, "Weekly")
                if sent:
                    emails_sent += 1
            return f"Sent weekly digest to {emails_sent} users."
    return run_async_task(run())
