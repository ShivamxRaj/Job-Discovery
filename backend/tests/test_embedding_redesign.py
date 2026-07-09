import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from app.models.models import Job, JobEmbedding, Company, JobSource
from app.services.job_service import job_service
from app.services.embedding_service import embedding_service
from app.services.matching_service import matching_service
from app.db.session import AsyncSession

@pytest.mark.asyncio
async def test_job_ingestion_decoupled_from_embedding(db_session: AsyncSession):
    raw_job = {
        "title": "Software Engineer",
        "company_name": "Test Decoupled Company",
        "location": "Remote",
        "job_type": "Full-time",
        "url": "https://test.com/decoupled-job-1",
        "description": "Awesome python role",
        "skills": ["python"]
    }

    # Ingest job - should succeed synchronously without making OpenAI API calls
    job = await job_service.ingest_job(db_session, raw_job, "TestIngest")
    
    assert job.id is not None
    assert job.embedding_status == "PENDING"
    assert job.embedding_error is None

    # Verify no embedding was created yet
    emb_res = await db_session.execute(
        select(JobEmbedding).where(JobEmbedding.job_id == job.id)
    )
    assert emb_res.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_embedding_queue_processing_success(db_session: AsyncSession):
    raw_job = {
        "title": "Data Scientist",
        "company_name": "Queue Success Company",
        "location": "New York",
        "job_type": "Full-time",
        "url": "https://test.com/queue-job-1",
        "description": "Spark and pandas role",
        "skills": ["pandas"]
    }
    job = await job_service.ingest_job(db_session, raw_job, "QueueIngest")

    # Process queue with mocked successful OpenAI call
    mock_vector = [0.1] * 1536
    with patch("app.services.openai_service.openai_service.get_embedding", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_vector
        summary = await embedding_service.process_pending_embeddings(db_session, batch_size=5)

        assert summary["attempted"] >= 1
        assert summary["completed"] >= 1
        assert summary["rate_limited"] is False

    # Check database updates
    await db_session.refresh(job)
    assert job.embedding_status == "COMPLETED"
    assert job.embedding_error is None

    emb_res = await db_session.execute(
        select(JobEmbedding).where(JobEmbedding.job_id == job.id)
    )
    embedding_record = emb_res.scalar_one_or_none()
    assert embedding_record is not None
    assert abs(embedding_record.embedding[0] - 0.1) < 1e-5

@pytest.mark.asyncio
async def test_embedding_queue_processing_rate_limit_failure(db_session: AsyncSession):
    raw_job = {
        "title": "DevOps Engineer",
        "company_name": "Queue 429 Company",
        "location": "Remote",
        "job_type": "Full-time",
        "url": "https://test.com/queue-job-429",
        "description": "Kubernetes role",
        "skills": ["kubernetes"]
    }
    job = await job_service.ingest_job(db_session, raw_job, "QueueIngest429")

    # Process queue with mocked 429 Rate Limit error
    with patch("app.services.openai_service.openai_service.get_embedding", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("OpenAI API error: Status 429 - Rate Limit Exceeded")
        summary = await embedding_service.process_pending_embeddings(db_session, batch_size=5)

        assert summary["attempted"] >= 1
        assert summary["failed"] == 0
        assert summary["rate_limited"] is True

    # Check status was reverted to PENDING and error stored
    await db_session.refresh(job)
    assert job.embedding_status == "PENDING"
    assert "RateLimitReached" in job.embedding_error
