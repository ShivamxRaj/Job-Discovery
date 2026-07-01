"""
Integration tests — Resume Pipeline (Phase 2B)
-----------------------------------------------
Tests the full upload → parse → score → embed pipeline via the HTTP API.
Uses the in-memory SQLite test client from conftest.py.
External services (storage, OpenAI) are mocked.
"""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_FAKE_PARSED_JSON = {
    "summary": "Backend engineer with 4 years of Python and cloud experience.",
    "skills": [
        {"name": "Python", "years": 4},
        {"name": "FastAPI", "years": 2},
        {"name": "PostgreSQL", "years": 3},
        {"name": "Docker", "years": 2},
        {"name": "AWS", "years": 1},
        {"name": "React", "years": 1},
        {"name": "Redis", "years": 1},
        {"name": "Go", "years": 0.5},
    ],
    "experience": [
        {
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "description": "Built REST API serving 500k requests/day, reduced latency by 35%.",
        },
        {
            "title": "Junior Developer",
            "company": "Beta Ltd",
            "description": "Maintained Django services for 100+ clients.",
        },
    ],
    "education": [{"degree": "B.S. Computer Science", "school": "State University", "year": 2020}],
    "certifications": [{"name": "AWS Solutions Architect Associate"}],
    "projects": [{"title": "Open-source FastAPI boilerplate", "description": "1000+ GitHub stars"}],
    "quality_score": None,   # must NOT be used by service; deterministic engine computes this
    "ats_score": None,
    "suggestions": [],
}

_RESUME_TEXT = (
    "jane.smith@example.com\n"
    "Backend engineer with 4 years of Python and cloud experience.\n\n"
    "Experience:\n"
    "Backend Engineer, Acme Corp 2021-2024\n"
    "Built REST API serving 500k requests/day, reduced latency by 35%.\n\n"
    "Junior Developer, Beta Ltd 2020-2021\n"
    "Maintained Django services for 100+ clients.\n\n"
    "Education:\nB.S. Computer Science, State University 2020\n\n"
    "Skills: Python FastAPI PostgreSQL Docker AWS React Redis Go\n\n"
    "Certifications: AWS Solutions Architect Associate\n\n"
    "Projects: Open-source FastAPI boilerplate — 1000+ GitHub stars\n"
)

_FAKE_EMBEDDING = [0.01 * i for i in range(1536)]  # non-zero, 1536-dim


def _make_resume_file(text: str = _RESUME_TEXT, filename: str = "resume.txt") -> dict:
    return {
        "file": (filename, io.BytesIO(text.encode()), "text/plain"),
        "title": (None, "Integration Test Resume"),
    }


async def _register_and_login(client) -> dict:
    """Helper: register user and return token dict."""
    await client.post("/api/v1/auth/register", json={
        "email": "resume_test@example.com",
        "password": "testpass123"
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": "resume_test@example.com",
        "password": "testpass123"
    })
    return res.json()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_upload_resume_full_pipeline(mock_openai, mock_storage, client):
    """
    Upload → AI parse → deterministic score → skill normalization → embedding.
    Asserts:
      - 201 Created
      - quality_score is computed (not None, not a hardcoded 70)
      - ats_score is computed
      - skills are normalized (aliases resolved)
      - ocr_status = READY
      - embedding verification metadata available
    """
    mock_storage.upload_file = AsyncMock(return_value="http://fake/resume.txt")
    mock_storage.delete_file = AsyncMock()
    mock_openai.parse_resume = AsyncMock(return_value=_FAKE_PARSED_JSON)
    mock_openai.get_embedding = AsyncMock(return_value=_FAKE_EMBEDDING)

    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    res = await client.post(
        "/api/v1/resumes/upload",
        files=_make_resume_file(),
        headers=headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()

    # OCR status
    assert data["ocr_status"] == "READY"

    # Parsed data present
    assert data["parsed_data"] is not None
    pd = data["parsed_data"]

    # Scores are deterministic — never null for a valid text resume
    assert pd["quality_score"] is not None, "Quality score must not be None for a text resume"
    assert pd["ats_score"] is not None, "ATS score must not be None for a text resume"
    assert pd["quality_score_reason"] is None, "No error expected; reason must be None"
    assert pd["ats_score_reason"] is None

    # Scores are not magic defaults
    assert pd["quality_score"] != 70.0, "Score must not be the old hardcoded default 70.0"
    assert pd["ats_score"] != 70.0

    # Scores are in valid range
    assert 0.0 <= pd["quality_score"] <= 100.0
    assert 0.0 <= pd["ats_score"] <= 100.0

    # Suggestions present (list, even if empty for a good resume)
    assert isinstance(pd["suggestions"], list)

    # Skills normalized
    skill_names = [s["skill_name"] for s in data["skills"]]
    assert "Python" in skill_names                # canonical
    assert "FastAPI" in skill_names
    assert "PostgreSQL" in skill_names            # alias 'postgres' → 'PostgreSQL'

    # Embedding mock was called
    mock_openai.get_embedding.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_upload_ocr_pending_scores_null(mock_openai, mock_storage, client):
    """
    Upload a file that yields < 50 chars of text → ocr_status = PENDING_OCR,
    quality_score and ats_score must be null with a machine-readable reason.
    """
    mock_storage.upload_file = AsyncMock(return_value="http://fake/scan.pdf")
    mock_storage.delete_file = AsyncMock()
    # This simulates a binary PDF: parser returns almost empty text.
    # We patch extract_resume_text to return < 50 chars.

    with patch("app.services.resume_service.extract_resume_text", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = "  "   # fewer than 50 chars

        tokens = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        res = await client.post(
            "/api/v1/resumes/upload",
            files={
                "file": ("scan.pdf", io.BytesIO(b"%PDF-binary"), "application/pdf"),
                "title": (None, "Scanned Resume"),
            },
            headers=headers,
        )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["ocr_status"] == "PENDING_OCR"
    pd = data["parsed_data"]
    assert pd is not None
    assert pd["quality_score"] is None
    assert pd["ats_score"] is None
    assert pd["quality_score_reason"] is not None
    assert pd["ats_score_reason"] is not None
    # OpenAI should NOT have been called
    mock_openai.parse_resume.assert_not_called()
    mock_openai.get_embedding.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_upload_rollback_on_openai_failure(mock_openai, mock_storage, client):
    """
    If OpenAI embedding fails, transaction rolls back and uploaded file is deleted.
    """
    mock_storage.upload_file = AsyncMock(return_value="http://fake/resume.txt")
    mock_openai.parse_resume = AsyncMock(return_value=_FAKE_PARSED_JSON)
    mock_openai.get_embedding = AsyncMock(side_effect=RuntimeError("OpenAI unavailable"))

    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    with patch("app.services.celery_app.delete_storage_file_task.delay") as mock_delay:
        res = await client.post(
            "/api/v1/resumes/upload",
            files=_make_resume_file(),
            headers=headers,
        )
    assert res.status_code == 500, res.text
    # Storage cleanup must be triggered asynchronously via Celery
    mock_delay.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_list_resumes_after_upload(mock_openai, mock_storage, client):
    """GET / returns the uploaded resume in the list."""
    mock_storage.upload_file = AsyncMock(return_value="http://fake/resume.txt")
    mock_storage.delete_file = AsyncMock()
    mock_openai.parse_resume = AsyncMock(return_value=_FAKE_PARSED_JSON)
    mock_openai.get_embedding = AsyncMock(return_value=_FAKE_EMBEDDING)

    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    await client.post("/api/v1/resumes/upload", files=_make_resume_file(), headers=headers)
    res = await client.get("/api/v1/resumes", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_get_version_detail_scores(mock_openai, mock_storage, client):
    """GET /versions/{id} returns non-null deterministic scores."""
    mock_storage.upload_file = AsyncMock(return_value="http://fake/resume.txt")
    mock_storage.delete_file = AsyncMock()
    mock_openai.parse_resume = AsyncMock(return_value=_FAKE_PARSED_JSON)
    mock_openai.get_embedding = AsyncMock(return_value=_FAKE_EMBEDDING)

    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    upload_res = await client.post(
        "/api/v1/resumes/upload", files=_make_resume_file(), headers=headers
    )
    version_id = upload_res.json()["id"]

    res = await client.get(f"/api/v1/resumes/versions/{version_id}", headers=headers)
    assert res.status_code == 200
    pd = res.json()["parsed_data"]
    assert pd["quality_score"] is not None
    assert pd["ats_score"] is not None


@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_embedding_verification_endpoint(mock_openai, mock_storage, client):
    """
    GET /versions/{id}/embedding returns:
      - model name
      - dimensions = 1536
      - is_non_null = True
      - is_non_zero = True
      - 5 sample values
    """
    mock_storage.upload_file = AsyncMock(return_value="http://fake/resume.txt")
    mock_storage.delete_file = AsyncMock()
    mock_openai.parse_resume = AsyncMock(return_value=_FAKE_PARSED_JSON)
    mock_openai.get_embedding = AsyncMock(return_value=_FAKE_EMBEDDING)

    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    upload_res = await client.post(
        "/api/v1/resumes/upload", files=_make_resume_file(), headers=headers
    )
    version_id = upload_res.json()["id"]

    res = await client.get(f"/api/v1/resumes/versions/{version_id}/embedding", headers=headers)
    assert res.status_code == 200, res.text
    emb = res.json()

    assert emb["model"] == "text-embedding-3-small"
    assert emb["dimensions"] == 1536
    assert emb["is_non_null"] is True
    assert emb["is_non_zero"] is True
    assert len(emb["sample_values"]) == 5


@pytest.mark.asyncio
@patch("app.services.resume_service.storage_manager")
@patch("app.services.resume_service.openai_service")
async def test_analyze_endpoint_recomputes_scores(mock_openai, mock_storage, client):
    """GET /versions/{id}/analyze recomputes scores from stored data."""
    mock_storage.upload_file = AsyncMock(return_value="http://fake/resume.txt")
    mock_storage.delete_file = AsyncMock()
    mock_openai.parse_resume = AsyncMock(return_value=_FAKE_PARSED_JSON)
    mock_openai.get_embedding = AsyncMock(return_value=_FAKE_EMBEDDING)

    tokens = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    upload_res = await client.post(
        "/api/v1/resumes/upload", files=_make_resume_file(), headers=headers
    )
    version_id = upload_res.json()["id"]

    res = await client.get(f"/api/v1/resumes/versions/{version_id}/analyze", headers=headers)
    assert res.status_code == 200, res.text
    pd = res.json()["parsed_data"]
    assert pd["quality_score"] is not None
    assert pd["ats_score"] is not None
