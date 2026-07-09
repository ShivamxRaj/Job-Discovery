import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select, func
from app.core.config import settings
from app.services.job_service import job_service
from app.repositories.job import job_repo
from app.models.models import Job, Company

@pytest.mark.asyncio
async def test_development_mode_inserts_seed_jobs(db_session):
    # Mock httpx.AsyncClient.get to throw an exception so it uses fallback/seed data
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("API offline")
        
        # Enable development environment
        settings.ENVIRONMENT = "development"
        settings.DEBUG = True
        
        # Run ingestion
        count = await job_service.aggregate_jobs_from_remote_apis(db_session)
        
        # Check if seed jobs are inserted
        assert count > 0
        
        # Query database directly to count seed jobs
        query = select(func.count(Job.id)).where(Job.is_seed_data == True)
        seed_count = (await db_session.execute(query)).scalar()
        assert seed_count > 0
        assert seed_count == count

        # Verify data_origin is SEED
        res = await db_session.execute(select(Job).where(Job.is_seed_data == True).limit(1))
        job = res.scalar()
        assert job.data_origin == "SEED"

@pytest.mark.asyncio
async def test_production_mode_inserts_zero_seed_jobs(db_session):
    # Mock httpx.AsyncClient.get to throw an exception to simulate feed failures
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("API offline")
        
        # Enable production environment
        settings.ENVIRONMENT = "production"
        settings.DEBUG = False
        
        # Run ingestion
        count = await job_service.aggregate_jobs_from_remote_apis(db_session)
        
        # Seed jobs must not be loaded
        assert count == 0
        
        # Query database directly to ensure zero seed jobs exist
        query = select(func.count(Job.id)).where(Job.is_seed_data == True)
        seed_count = (await db_session.execute(query)).scalar()
        assert seed_count == 0

@pytest.mark.asyncio
async def test_centralized_query_filter_default_path(db_session):
    # Create a mock company first
    company = Company(
        name="Test Corp",
        normalized_name="test corp"
    )
    db_session.add(company)
    await db_session.flush()

    # Add a mock seed job and a mock real job to db manually
    seed_job = Job(
        title="Mock Seed",
        normalized_title="Mock Seed",
        description="Desc",
        location="Remote",
        job_type="Full-time",
        url="https://seed.job",
        is_seed_data=True,
        data_origin="SEED",
        is_active=True,
        company_id=company.id
    )
    real_job = Job(
        title="Mock Real",
        normalized_title="Mock Real",
        description="Desc",
        location="Remote",
        job_type="Full-time",
        url="https://real.job",
        is_seed_data=False,
        data_origin="REMOTE_OK",
        is_active=True,
        company_id=company.id
    )
    db_session.add_all([seed_job, real_job])
    await db_session.flush()

    # Case 1: Simulation of Production mode (default query path)
    settings.ENVIRONMENT = "production"
    settings.DEBUG = False
    
    query = select(Job)
    prod_query = job_repo.apply_production_filter(query, include_seed=False)
    results = (await db_session.execute(prod_query)).scalars().all()
    
    # In production, seed job must be excluded
    assert len(results) == 1
    assert results[0].url == "https://real.job"

    # Case 2: Simulation of Development mode explicitly opting in
    settings.ENVIRONMENT = "development"
    settings.DEBUG = True
    
    dev_query = job_repo.apply_production_filter(query, include_seed=True)
    results_dev = (await db_session.execute(dev_query)).scalars().all()
    
    # In development, both must be returned
    assert len(results_dev) == 2
