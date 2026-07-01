import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.resume_service import resume_service
from app.models.models import CleanupJob
from app.repositories.cleanup import cleanup_repo
from app.services.celery_app import delete_storage_file_async, process_cleanup_jobs_async

LONG_RESUME_TEXT = (
    "john.doe@example.com\n"
    "Experienced software engineer with 5 years building scalable web services.\n"
    "Skills: Python, Docker, React, PostgreSQL.\n"
    "Experience: Senior Engineer at Acme Corp, led a team of 6 engineers."
)


@pytest.mark.asyncio
@patch("app.services.resume_service.extract_resume_text", new_callable=AsyncMock)
@patch("app.services.resume_service.storage_manager", new_callable=MagicMock)
@patch("app.services.resume_service.openai_service", new_callable=MagicMock)
async def test_cleanup_job_creation_on_rollback(
    mock_openai, mock_storage, mock_extract, db_session
):
    """
    Test that when an upload transaction fails (e.g., OpenAI fails), 
    a CleanupJob is correctly registered in the database, and the transaction is rolled back.
    """
    mock_extract.return_value = LONG_RESUME_TEXT
    mock_storage.upload_file = AsyncMock(return_value="http://fake-supabase/resume_fail.pdf")
    
    # Trigger exception on OpenAI parse to force rollback
    mock_openai.parse_resume = AsyncMock(side_effect=Exception("OpenAI Parse Failed"))

    fake_file = MagicMock(spec=UploadFile)
    fake_file.filename = "resume_fail.pdf"
    fake_file.read = AsyncMock(return_value=b"PDF contents")
    fake_file.seek = AsyncMock()

    user_id = 1

    # Run upload and verify that it throws the original error
    with pytest.raises(Exception, match="OpenAI Parse Failed"):
        # We patch delay() to prevent Celery from actually trying to call broker in unit test
        with patch("app.services.celery_app.delete_storage_file_task.delay") as mock_delay:
            await resume_service.upload_and_parse_resume(
                db_session, user_id=user_id, file=fake_file, title="Test Resume"
            )

    # Verify that a CleanupJob was persisted in the DB
    query = select(CleanupJob).where(CleanupJob.file_path == "resumes/1_1_v1_resume_fail.pdf")
    result = await db_session.execute(query)
    job = result.scalar_one_or_none()
    
    assert job is not None
    assert job.status == "PENDING"
    assert job.retry_count == 0


@pytest.mark.asyncio
@patch("app.utils.storage.storage_manager.delete_file", new_callable=AsyncMock)
async def test_delete_success(mock_delete, db_session):
    """
    Test that a successful deletion marks the cleanup job as SUCCESS.
    """
    mock_delete.return_value = None

    # Register a new cleanup job
    job = await cleanup_repo.create_job(db_session, file_path="resumes/test_success.pdf")
    await db_session.commit()
    
    # Extract ID before session expiration
    job_id = job.id

    # Invoke the async logic directly, passing the test db_session
    await delete_storage_file_async(job_id, db=db_session)

    # Refresh job from DB and verify status
    db_session.expire_all()
    updated_job = await cleanup_repo.get(db_session, job_id)
    assert updated_job is not None
    assert updated_job.status == "SUCCESS"
    assert updated_job.error_message is None
    mock_delete.assert_called_once_with("resumes/test_success.pdf")


@pytest.mark.asyncio
@patch("app.utils.storage.storage_manager.delete_file", new_callable=AsyncMock)
async def test_delete_permanent_failure(mock_delete, db_session):
    """
    Test that repeated failures increment the retry count, and eventually 
    transitions the status to PERMANENT_FAILURE once max_retries is reached.
    """
    mock_delete.side_effect = Exception("Supabase connection timed out")

    # Create a job with max_retries=3 to make the test faster
    job = CleanupJob(
        file_path="resumes/test_fail.pdf",
        status="PENDING",
        retry_count=0,
        max_retries=3
    )
    db_session.add(job)
    await db_session.commit()
    
    # Extract ID before session expiration
    job_id = job.id

    # Run the task 3 times (equal to max_retries)
    for i in range(3):
        await delete_storage_file_async(job_id, db=db_session)
        db_session.expire_all()

    # Verify status is now PERMANENT_FAILURE
    updated_job = await cleanup_repo.get(db_session, job_id)
    assert updated_job is not None
    assert updated_job.status == "PERMANENT_FAILURE"
    assert updated_job.retry_count == 3
    assert "Supabase connection timed out" in updated_job.error_message


@pytest.mark.asyncio
@patch("app.utils.storage.storage_manager.delete_file", new_callable=AsyncMock)
async def test_retry_worker_process_jobs(mock_delete, db_session):
    """
    Test that process_cleanup_jobs_async processes all pending/failed jobs in one batch.
    """
    mock_delete.return_value = None

    # Clear any old cleanup jobs
    from sqlalchemy import delete
    await db_session.execute(delete(CleanupJob))
    await db_session.commit()

    # Create two pending jobs
    job1 = await cleanup_repo.create_job(db_session, file_path="resumes/job1.pdf")
    job2 = await cleanup_repo.create_job(db_session, file_path="resumes/job2.pdf")
    await db_session.commit()
    
    # Extract IDs before session expiration
    job1_id = job1.id
    job2_id = job2.id

    # Run the batch retry task, passing the test db_session
    await process_cleanup_jobs_async(db=db_session)

    # Verify both jobs succeeded
    db_session.expire_all()
    j1 = await cleanup_repo.get(db_session, job1_id)
    j2 = await cleanup_repo.get(db_session, job2_id)

    assert j1.status == "SUCCESS"
    assert j2.status == "SUCCESS"
    assert mock_delete.call_count == 2
