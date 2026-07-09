import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select, func
from app.models.models import RawJob, Job, Company
from app.services.ingestion_service import ingestion_service

@pytest.mark.asyncio
async def test_process_pending_raw_jobs_success(db_session):
    # Setup: Create a pending raw job
    raw_job = RawJob(
        source="RemoteOK",
        source_job_id="12345",
        url="https://remoteok.com/test-job-url",
        title="Sr. React Dev",
        company_name="Vercel Inc.",
        description="Looking for react engineer.",
        location="Remote",
        job_type="Full-time",
        is_remote=True,
        skills=["React", "TypeScript"],
        status="PENDING"
    )
    db_session.add(raw_job)
    await db_session.commit()
    raw_job_id = raw_job.id

    # Mock OpenAI embedding generation to avoid real API calls
    mock_vector = [0.1] * 1536
    with patch("app.services.openai_service.openai_service.get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.return_value = mock_vector
        
        # Trigger queue processing
        res = await ingestion_service.process_pending_raw_jobs(db_session, batch_size=5)
        
        assert res["processed"] == 1
        assert res["failed"] == 0
        assert res["total_attempted"] == 1
        
        # Assert raw job status is updated to PROCESSED
        refreshed_raw = (await db_session.execute(
            select(RawJob).where(RawJob.id == raw_job_id)
        )).scalar()
        assert refreshed_raw.status == "PROCESSED"
        assert refreshed_raw.error_message is None
        
        # Assert job is successfully created in jobs table with correct normalization
        refreshed_job = (await db_session.execute(
            select(Job).where(Job.url == "https://remoteok.com/test-job-url")
        )).scalar()
        assert refreshed_job is not None
        assert refreshed_job.title == "Sr. React Dev"
        assert refreshed_job.normalized_title == "Senior React Developer" # Title normalization check
        assert refreshed_job.data_origin == "RemoteOK"
        
        # Company normalization check (Vercel Inc. -> Vercel)
        company = (await db_session.execute(
            select(Company).where(Company.id == refreshed_job.company_id)
        )).scalar()
        assert company.name == "Vercel Inc."
        assert company.normalized_name == "vercel"

@pytest.mark.asyncio
async def test_process_pending_raw_jobs_failure(db_session):
    # Setup: Create another pending raw job
    raw_job = RawJob(
        source="Arbeitnow",
        source_job_id="67890",
        url="https://arbeitnow.com/test-job-fail",
        title="Python Engineer",
        company_name="Failed Corp",
        description="Will fail during embedding.",
        status="PENDING"
    )
    db_session.add(raw_job)
    await db_session.commit()
    raw_job_id = raw_job.id

    # 1. Trigger queue processing - should succeed (processed == 1) because embedding is decoupled
    res = await ingestion_service.process_pending_raw_jobs(db_session, batch_size=5)
    
    assert res["processed"] == 1
    assert res["failed"] == 0
    
    # Assert raw job status is updated to PROCESSED
    refreshed_raw = (await db_session.execute(
        select(RawJob).where(RawJob.id == raw_job_id)
    )).scalar()
    assert refreshed_raw.status == "PROCESSED"

    # Assert promoted job is created with status PENDING
    refreshed_job = (await db_session.execute(
        select(Job).where(Job.url == "https://arbeitnow.com/test-job-fail")
    )).scalar()
    assert refreshed_job is not None
    assert refreshed_job.embedding_status == "PENDING"

    # 2. Trigger asynchronous embedding processing with a failing mock
    from app.services.embedding_service import embedding_service
    with patch("app.services.openai_service.openai_service.get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.side_effect = Exception("OpenAI API error")
        
        summary = await embedding_service.process_pending_embeddings(db_session, batch_size=5)
        
        assert summary["failed"] == 1
        
        # Assert status updated to FAILED and error stored in job record
        await db_session.refresh(refreshed_job)
        assert refreshed_job.embedding_status == "FAILED"
        assert "OpenAI API error" in refreshed_job.embedding_error

