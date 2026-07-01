import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.connectors.base import BaseConnector, retry_on_http_failure
from app.services.connectors.remoteok import RemoteOKConnector
from app.services.connectors.arbeitnow import ArbeitnowConnector
from app.services.connectors.adzuna import AdzunaConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector

from app.services.ingestion_service import ingestion_service
from app.models.models import RawJob
from app.schemas.schemas import RawJobData


# Mock connector to test retry decorator
class FakeConnector(BaseConnector):
    def get_name(self) -> str:
        return "FakeConnector"

    @retry_on_http_failure(max_retries=3, initial_delay=0.01)
    async def fetch_jobs(self, limit: int = 15) -> list:
        return await self._impl()

    async def _impl(self):
        return []

    async def check_health(self) -> tuple:
        return True, "Healthy"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Retry Logic Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_logic_eventual_success():
    connector = FakeConnector()
    call_count = 0

    async def mock_impl():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary error")
        return [{"job": "data"}]

    connector._impl = mock_impl
    res = await connector.fetch_jobs()
    assert res == [{"job": "data"}]
    assert call_count == 3  # Try 1 (fail), Try 2 (fail), Try 3 (success)


@pytest.mark.asyncio
async def test_retry_logic_max_failures():
    connector = FakeConnector()
    call_count = 0

    async def mock_impl():
        nonlocal call_count
        call_count += 1
        raise Exception("Permanent error")

    connector._impl = mock_impl
    with pytest.raises(Exception, match="Permanent error"):
        await connector.fetch_jobs()
    
    assert call_count == 4  # Initial try + 3 retries


# ─────────────────────────────────────────────────────────────────────────────
# 2. Connectors Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_remoteok_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"legal": "Copyright 2026 RemoteOK"},
        {
            "id": 12345,
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
    assert jobs[0].source_job_id == "12345"
    assert jobs[0].title == "Staff Engineer"
    assert jobs[0].company_name == "RemoteCorp"
    assert jobs[0].url == "https://remoteok.com/jobs/123"
    assert jobs[0].is_remote is True
    assert "Python" in jobs[0].skills

    healthy, msg = await connector.check_health()
    assert healthy is True
    assert "Healthy" in msg


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_arbeitnow_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "slug": "django-developer-berlin-tech-123",
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
    assert jobs[0].source_job_id == "django-developer-berlin-tech-123"
    assert jobs[0].title == "Django Developer"
    assert jobs[0].company_name == "Berlin Tech"
    assert jobs[0].is_remote is True

    healthy, msg = await connector.check_health()
    assert healthy is True


@pytest.mark.asyncio
@patch("app.services.connectors.adzuna.settings")
@patch("httpx.AsyncClient.get")
async def test_adzuna_connector_without_credentials(mock_get, mock_settings):
    mock_settings.ADZUNA_APP_ID = None
    mock_settings.ADZUNA_APP_KEY = None

    connector = AdzunaConnector()
    jobs = await connector.fetch_jobs(limit=5)
    assert len(jobs) == 0

    healthy, msg = await connector.check_health()
    assert healthy is False
    assert "Missing credentials" in msg


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
                "id": "adz-123",
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
    assert jobs[0].source_job_id == "adz-123"
    assert jobs[0].title == "Python Architect"
    assert jobs[0].company_name == "CloudCorp"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_greenhouse_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [
            {
                "id": 9876,
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
    assert jobs[0].source_job_id == "9876"
    assert jobs[0].title == "Full Stack Dev"
    assert jobs[0].company_name == "Stripe"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_lever_connector_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "lev-111",
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
    assert jobs[0].source_job_id == "lev-111"
    assert jobs[0].title == "Data Scientist"
    assert jobs[0].company_name == "Vercel"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Ingestion Service & Staging DB Queue Tests
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
    from sqlalchemy import delete
    await db_session.execute(delete(RawJob))
    await db_session.commit()

    mock_remoteok_fetch.return_value = [
        RawJobData(
            source_job_id="ro-99",
            title="SRE",
            company_name="Acme",
            description="Acme SRE",
            url="https://job-url.com/sre",
            location="Remote"
        )
    ]
    mock_arbeitnow_fetch.return_value = []
    mock_adzuna_fetch.return_value = []
    mock_greenhouse_fetch.return_value = []
    mock_lever_fetch.return_value = []

    res = await ingestion_service.ingest_from_all_connectors(db_session, limit_per_connector=5)
    assert res["RemoteOK"]["inserted"] == 1

    res_second = await ingestion_service.ingest_from_all_connectors(db_session, limit_per_connector=5)
    assert res_second["RemoteOK"]["inserted"] == 0
    assert res_second["RemoteOK"]["duplicates"] == 1

    query = select(RawJob).where(RawJob.url == "https://job-url.com/sre")
    db_res = await db_session.execute(query)
    raw_job = db_res.scalar_one_or_none()

    assert raw_job is not None
    assert raw_job.source_job_id == "ro-99"
    assert raw_job.status == "PENDING"


# ─────────────────────────────────────────────────────────────────────────────
# 4. HTTP Endpoint Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingestion_health_endpoint(client, db_session):
    from tests.test_resume_integration import _register_and_login
    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    with patch("app.services.ingestion_service.ingestion_service.check_connectors_health") as mock_health:
        mock_health.return_value = {
            "status": "degraded",
            "timestamp": "2026-07-01T12:00:00Z",
            "connectors": {
                "RemoteOK": {"healthy": True, "status": "HEALTHY", "message": "Healthy"},
                "Adzuna": {"healthy": False, "status": "UNHEALTHY", "message": "Missing credentials"}
            }
        }

        res = await client.get("/api/v1/jobs/ingestion/health", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["connectors"]["Adzuna"]["status"] == "UNHEALTHY"


@pytest.mark.asyncio
async def test_ingestion_sync_endpoint(client, db_session):
    from tests.test_resume_integration import _register_and_login
    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    with patch("app.services.ingestion_service.ingestion_service.ingest_from_connector") as mock_ingest:
        mock_ingest.return_value = {
            "jobs_fetched": 10,
            "jobs_inserted": 8,
            "duplicates": 2,
            "duration_ms": 120
        }

        res = await client.post("/api/v1/jobs/sync/remoteok", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["jobs_fetched"] == 10
        assert data["jobs_inserted"] == 8
        assert data["duplicates"] == 2
        assert data["duration_ms"] == 120
