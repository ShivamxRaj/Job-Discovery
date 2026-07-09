from celery import Celery
from celery.schedules import crontab
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    "retry-failed-cleanups-hourly": {
        "task": "tasks.process_cleanup_jobs",
        "schedule": crontab(minute="0"),
    },
    "ingest-raw-jobs-daily": {
        "task": "tasks.ingest_raw_jobs",
        "schedule": crontab(hour="2", minute="0"), # Daily at 2 AM
    },
    "process-raw-jobs-hourly": {
        "task": "tasks.process_raw_jobs_queue",
        "schedule": crontab(minute="*/30"), # Run every 30 minutes
    },
    # --- KNOWN OPERATIONAL LIMITATION (TD-006) ---
    # Provider: GitHub Models (text-embedding-3-small)
    # Hard limit: 150 requests/day/model (free tier)
    # Strategy: Run once daily at 00:05 UTC (5 min after quota reset)
    # with full batch of 150. Clears ~150 PENDING jobs per day.
    # This constraint is ACCEPTED until user growth justifies paid tier.
    "process-job-embeddings-daily-at-midnight": {
        "task": "tasks.process_job_embeddings_daily",
        "schedule": crontab(hour="0", minute="5"),  # 00:05 UTC daily
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


async def process_cleanup_jobs_async(db: Optional[AsyncSession] = None) -> str:
    """Internal async executor for processing pending cleanup jobs."""
    from app.repositories.cleanup import cleanup_repo
    from app.utils.storage import storage_manager

    async def run_with_db(session: AsyncSession):
        jobs = await cleanup_repo.get_pending_jobs(session)
        if not jobs:
            return "No pending cleanup jobs found."

        processed = 0
        for job in jobs:
            # Extract variables before database commit to prevent lazy-load expiration issues
            file_path = job.file_path
            job_id = job.id

            # Mark as processing
            job.status = "PROCESSING"
            session.add(job)
            await session.commit()

            try:
                # Execute actual deletion from storage
                await storage_manager.delete_file(file_path)
                await cleanup_repo.mark_success(session, job_id=job_id)
                processed += 1
            except Exception as e:
                await cleanup_repo.mark_failed(session, job_id=job_id, error_message=str(e))
            
            await session.commit()

        return f"Processed {len(jobs)} cleanup jobs (Successes: {processed})."

    if db is not None:
        return await run_with_db(db)
    else:
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            return await run_with_db(session)


async def delete_storage_file_async(job_id: int, db: Optional[AsyncSession] = None) -> str:
    """Internal async executor for deleting a specific storage file."""
    from app.repositories.cleanup import cleanup_repo
    from app.utils.storage import storage_manager

    async def run_with_db(session: AsyncSession):
        job = await cleanup_repo.get(session, job_id)
        if not job or job.status == "SUCCESS":
            return f"Job {job_id} not found or already success."
        
        file_path = job.file_path
        
        job.status = "PROCESSING"
        session.add(job)
        await session.commit()

        try:
            await storage_manager.delete_file(file_path)
            await cleanup_repo.mark_success(session, job_id=job.id)
        except Exception as e:
            await cleanup_repo.mark_failed(session, job_id=job.id, error_message=str(e))
        
        await session.commit()
        return f"Executed job {job_id}."

    if db is not None:
        return await run_with_db(db)
    else:
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            return await run_with_db(session)


@celery.task(name="tasks.process_cleanup_jobs")
def process_cleanup_jobs_task():
    """Background task to fetch and execute pending file cleanup jobs from Supabase storage."""
    return run_async_task(process_cleanup_jobs_async())


@celery.task(name="tasks.delete_storage_file")
def delete_storage_file_task(job_id: int):
    """Background task to delete a specific storage file by job ID."""
    return run_async_task(delete_storage_file_async(job_id))


@celery.task(name="tasks.ingest_raw_jobs", bind=True, max_retries=3, default_retry_delay=300)
def ingest_raw_jobs_task(self):
    """Celery task to run all connectors and populate raw_jobs."""
    from app.db.session import async_session_maker
    from app.services.ingestion_service import ingestion_service
    
    async def run():
        async with async_session_maker() as db:
            return await ingestion_service.ingest_from_all_connectors(db)
    try:
        return run_async_task(run())
    except Exception as exc:
        # Retry on transient errors
        raise self.retry(exc=exc)


@celery.task(name="tasks.process_raw_jobs_queue")
def process_raw_jobs_queue_task():
    """Celery task to read pending raw jobs and ingest them into production jobs table."""
    from app.db.session import async_session_maker
    from app.services.ingestion_service import ingestion_service
    
    async def run():
        async with async_session_maker() as db:
            return await ingestion_service.process_pending_raw_jobs(db, batch_size=20)
    return run_async_task(run())


@celery.task(name="tasks.process_job_embeddings")
def process_job_embeddings_task():
    """Legacy embedding task (kept for backward compatibility). Not scheduled."""
    from app.db.session import async_session_maker
    from app.services.embedding_service import embedding_service
    async def run():
        async with async_session_maker() as db:
            return await embedding_service.process_pending_embeddings(db, batch_size=20)
    return run_async_task(run())


@celery.task(name="tasks.process_job_embeddings_daily")
def process_job_embeddings_daily_task():
    """Daily embedding scheduler — runs at 00:05 UTC to consume the full 150/day quota.
    
    This is the ONLY scheduled embedding task. Replaces the old every-5-min run.
    
    TD-006 Status: Known Operational Limitation.
    Provider: GitHub Models (text-embedding-3-small).
    Limit: 150 requests/day/model (free tier).
    Resolution: Migrate to paid tier when active users justify the cost.
    """
    import datetime
    from app.db.session import async_session_maker
    from app.services.embedding_service import embedding_service

    run_time = datetime.datetime.utcnow().isoformat()
    print(f"[EmbeddingScheduler] {run_time} UTC — Daily batch started.")

    async def run():
        async with async_session_maker() as db:
            # Count pending before run
            from sqlalchemy import text
            before = await db.execute(text(
                "SELECT COUNT(*) FROM jobs WHERE embedding_status = 'PENDING';"
            ))
            pending_before = before.scalar()

            # Process up to 150 (full daily quota)
            result = await embedding_service.process_pending_embeddings(db, batch_size=150)

            # Count remaining after run
            after = await db.execute(text(
                "SELECT COUNT(*) FROM jobs WHERE embedding_status = 'PENDING';"
            ))
            pending_after = after.scalar()

            print(
                f"[EmbeddingScheduler] Run complete. "
                f"Attempted={result['attempted']}, "
                f"Completed={result['completed']}, "
                f"Failed={result['failed']}, "
                f"RateLimited={result['rate_limited']}, "
                f"PendingBefore={pending_before}, "
                f"PendingAfter={pending_after}"
            )
            return result

    result = run_async_task(run())
    end_time = datetime.datetime.utcnow().isoformat()
    print(f"[EmbeddingScheduler] {end_time} UTC — Daily batch finished. Next run: tomorrow 00:05 UTC.")
    return result


@celery.task(name="tasks.retry_failed_resume")
def retry_failed_resume_task(version_id: int):
    """Celery task to retry parsing/embedding for a failed resume version."""
    from app.db.session import async_session_maker
    from app.services.resume_service import resume_service
    
    async def run():
        async with async_session_maker() as db:
            return await resume_service.retry_failed_stages(db, version_id)
    return run_async_task(run())


