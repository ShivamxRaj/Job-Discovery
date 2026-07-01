import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.connectors.remoteok import RemoteOKConnector
from app.services.connectors.arbeitnow import ArbeitnowConnector
from app.services.connectors.adzuna import AdzunaConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector

from app.services.ingestion_service import ingestion_service
from app.models.models import RawJob
from app.schemas.schemas import RawJobData


# ─────────────────────────────────────────────────────────────────────────────
# 1. Connectors Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_remoteok_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"legal": "Copyright 2026 RemoteOK"},
        {
            "position": "Staff Engineer",
            "company": "RemoteCorp",
            "description": "Job desc here",
            "location": "Worldwide",
            "url": "https://remoteok.com/jobs/123",
            "company_logo": "https://logo.png",
            "tags": ["Python", "Kubernetes"],
            "date": "2026-07-01T12:00:00Z"
        }
    ]
    mock_get.return_value = mock_response

    connector = RemoteOKConnector()
    jobs = await connector.fetch_jobs(limit=5)
    
    assert len(jobs) == 1
    assert isinstance(jobs[0], RawJobData)
    assert jobs[0].title == "Staff Engineer"
    assert jobs[0].company_name == "RemoteCorp"
    assert jobs[0].url == "https://remoteok.com/jobs/123"
    assert jobs[0].is_remote is True
    assert "Python" in jobs[0].skills


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_arbeitnow_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "title": "Django Developer",
                "company_name": "Berlin Tech",
                "description": "Arbeitnow desc",
                "location": "Berlin",
                "remote": True,
                "url": "https://arbeitnow.com/123",
                "tags": ["Python", "Django"],
                "created_at": 1719878400
            }
        ]
    }
    mock_get.return_value = mock_response

    connector = ArbeitnowConnector()
    jobs = await connector.fetch_jobs(limit=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Django Developer"
    assert jobs[0].company_name == "Berlin Tech"
    assert jobs[0].is_remote is True
    assert jobs[0].location == "Berlin"


@pytest.mark.asyncio
@patch("app.services.connectors.adzuna.settings")
@patch("httpx.AsyncClient.get")
async def test_adzuna_connector_without_credentials(mock_get, mock_settings):
    mock_settings.ADZUNA_APP_ID = None
    mock_settings.ADZUNA_APP_KEY = None

    connector = AdzunaConnector()
    jobs = await connector.fetch_jobs(limit=5)
    assert len(jobs) == 0

    healthy = await connector.check_health()
    assert healthy is False


@pytest.mark.asyncio
@patch("app.services.connectors.adzuna.settings")
@patch("httpx.AsyncClient.get")
async def test_adzuna_connector_with_credentials(mock_get, mock_settings):
    mock_settings.ADZUNA_APP_ID = "test-id"
    mock_settings.ADZUNA_APP_KEY = "test-key"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Python Architect",
                "company": {"display_name": "CloudCorp"},
                "description": "Adzuna description",
                "location": {"display_name": "Austin, TX"},
                "contract_time": "full_time",
                "redirect_url": "https://adzuna.com/123",
                "category": {"label": "IT Jobs"},
                "created": "2026-07-01T15:00:00Z"
            }
        ]
    }
    mock_get.return_value = mock_response

    connector = AdzunaConnector()
    jobs = await connector.fetch_jobs(limit=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Python Architect"
    assert jobs[0].company_name == "CloudCorp"
    assert jobs[0].location == "Austin, TX"
    assert jobs[0].job_type == "Full-time"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_greenhouse_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [
            {
                "title": "Full Stack Dev",
                "content": "Description info",
                "location": {"name": "Remote, US"},
                "absolute_url": "https://greenhouse.io/stripe/jobs/123",
                "updated_at": "2026-07-01T18:00:00Z"
            }
        ]
    }
    mock_get.return_value = mock_response

    connector = GreenhouseConnector()
    connector.companies = ["stripe"]
    jobs = await connector.fetch_jobs(limit=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Full Stack Dev"
    assert jobs[0].company_name == "Stripe"
    assert jobs[0].is_remote is True
    assert jobs[0].location == "Remote, US"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_lever_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "text": "Data Scientist",
            "description": "Lever desc",
            "hostedUrl": "https://lever.co/vercel/123",
            "createdAt": 1719878400000,
            "categories": {
                "location": "New York",
                "commitment": "Full-time",
                "team": "Data Science",
                "department": "Engineering"
            }
        }
    ]
    mock_get.return_value = mock_response

    connector = LeverConnector()
    connector.companies = ["vercel"]
    jobs = await connector.fetch_jobs(limit=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Data Scientist"
    assert jobs[0].company_name == "Vercel"
    assert jobs[0].location == "New York"
    assert jobs[0].job_type == "Full-time"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Ingestion Service & Staging DB Queue Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.connectors.remoteok.RemoteOKConnector.fetch_jobs")
@patch("app.services.connectors.arbeitnow.ArbeitnowConnector.fetch_jobs")
@patch("app.services.connectors.adzuna.AdzunaConnector.fetch_jobs")
@patch("app.services.connectors.greenhouse.GreenhouseConnector.fetch_jobs")
@patch("app.services.connectors.lever.LeverConnector.fetch_jobs")
async def test_ingestion_service_deduplication(
    mock_lever_fetch,
    mock_greenhouse_fetch,
    mock_adzuna_fetch,
    mock_arbeitnow_fetch,
    mock_remoteok_fetch,
    db_session
):
    # Clear staging raw jobs
    from sqlalchemy import delete
    await db_session.execute(delete(RawJob))
    await db_session.commit()

    # Stub fetches
    mock_remoteok_fetch.return_value = [
        RawJobData(
            title="SRE",
            company_name="Acme",
            description="Acme SRE",
            url="https://job-url.com/sre",
            location="Remote"
        )
    ]
    # Rest return empty list
    mock_arbeitnow_fetch.return_value = []
    mock_adzuna_fetch.return_value = []
    mock_greenhouse_fetch.return_value = []
    mock_lever_fetch.return_value = []

    # Run ingestion first time
    res = await ingestion_service.ingest_from_all_connectors(db_session, limit_per_connector=5)
    assert res["RemoteOK"]["inserted"] == 1

    # Run ingestion second time (should skip duplicate url)
    res_second = await ingestion_service.ingest_from_all_connectors(db_session, limit_per_connector=5)
    assert res_second["RemoteOK"]["inserted"] == 0

    # Verify stored raw job is "PENDING" and retains original raw state
    query = select(RawJob).where(RawJob.url == "https://job-url.com/sre")
    db_res = await db_session.execute(query)
    raw_job = db_res.scalar_one_or_none()

    assert raw_job is not None
    assert raw_job.title == "SRE"
    assert raw_job.company_name == "Acme"
    assert raw_job.status == "PENDING"


# ─────────────────────────────────────────────────────────────────────────────
# 3. HTTP Endpoint Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingestion_health_endpoint(client, db_session):
    # Register / login
    from tests.test_resume_integration import _register_and_login
    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    with patch("app.services.ingestion_service.ingestion_service.check_connectors_health") as mock_health:
        mock_health.return_value = {
            "status": "healthy",
            "timestamp": "2026-07-01T12:00:00Z",
            "connectors": {
                "RemoteOK": {"healthy": True},
                "Arbeitnow": {"healthy": True}
            }
        }

        res = await client.get("/api/v1/jobs/ingestion/health", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "RemoteOK" in data["connectors"]


@pytest.mark.asyncio
async def test_ingestion_trigger_endpoint(client, db_session):
    from tests.test_resume_integration import _register_and_login
    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    with patch("app.services.ingestion_service.ingestion_service.ingest_from_all_connectors") as mock_ingest:
        mock_ingest.return_value = {
            "RemoteOK": {"status": "success", "fetched": 1, "inserted": 1}
        }

        res = await client.post("/api/v1/jobs/ingestion/trigger", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "Raw ingestion triggered successfully" in data["message"]
        assert data["results"]["RemoteOK"]["status"] == "success"
