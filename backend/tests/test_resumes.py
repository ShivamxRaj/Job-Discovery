import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.resume_service import resume_service
from app.models.models import Resume, ResumeVersion
from app.repositories.resume import resume_repo

# Long text (> 50 chars) to bypass scanned PDF / PENDING_OCR check
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
async def test_upload_resume_success(
    mock_openai, mock_storage, mock_extract, db_session
):
    # Setup mocks
    mock_extract.return_value = LONG_RESUME_TEXT
    
    mock_storage.upload_file = AsyncMock(return_value="http://fake-supabase/resume.pdf")
    
    mock_openai.parse_resume = AsyncMock(return_value={
        "skills": ["Python", "Docker"],
        "education": [],
        "experience": [{"title": "Senior Engineer", "company": "Acme Corp", "description": "Led team"}],
        "quality_score": 90.0,
        "ats_score": 85.0,
        "suggestions": ["Add achievements"]
    })
    mock_openai.get_embedding = AsyncMock(return_value=[0.1] * 1536)

    # Mock UploadFile
    fake_file = MagicMock(spec=UploadFile)
    fake_file.filename = "resume.pdf"
    fake_file.read = AsyncMock(return_value=b"PDF contents")
    fake_file.seek = AsyncMock()

    # Create dummy user (or use user_id = 1)
    user_id = 1

    # Run upload
    version = await resume_service.upload_and_parse_resume(
        db_session, user_id=user_id, file=fake_file, title="Test Resume"
    )

    # Asserts
    assert version is not None
    assert version.version_number == 1
    assert version.file_path == "http://fake-supabase/resume.pdf"
    assert version.parsed_data.quality_score is not None
    assert 0.0 <= version.parsed_data.quality_score <= 100.0
    assert version.parsed_data.ats_score is not None
    assert 0.0 <= version.parsed_data.ats_score <= 100.0
    assert len(version.skills) == 2
    assert version.skills[0].skill_name in ["Python", "Docker"]
    
    # Verify storage upload was called
    mock_storage.upload_file.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.resume_service.extract_resume_text", new_callable=AsyncMock)
@patch("app.services.resume_service.storage_manager", new_callable=MagicMock)
@patch("app.services.resume_service.openai_service", new_callable=MagicMock)
async def test_upload_resume_failure_rollback(
    mock_openai, mock_storage, mock_extract, db_session
):
    # Setup mocks
    mock_extract.return_value = LONG_RESUME_TEXT
    
    mock_storage.upload_file = AsyncMock(return_value="http://fake-supabase/resume_fail.pdf")
    mock_storage.delete_file = AsyncMock()
    
    # Make OpenAI parse fail to trigger exception and rollback
    mock_openai.parse_resume = AsyncMock(side_effect=Exception("OpenAI Parse Failed"))

    # Mock UploadFile
    fake_file = MagicMock(spec=UploadFile)
    fake_file.filename = "resume_fail.pdf"
    fake_file.read = AsyncMock(return_value=b"PDF contents")
    fake_file.seek = AsyncMock()

    user_id = 1

    # Run upload and expect error
    with pytest.raises(Exception, match="OpenAI Parse Failed"):
        with patch("app.services.celery_app.delete_storage_file_task.delay") as mock_delay:
            await resume_service.upload_and_parse_resume(
                db_session, user_id=user_id, file=fake_file, title="Test Resume"
            )

    # Verify that the Celery deletion task was scheduled asynchronously
    mock_delay.assert_called_once()
