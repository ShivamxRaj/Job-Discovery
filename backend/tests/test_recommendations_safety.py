import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.models import JobRecommendation, User, Company, Job, Resume, ResumeVersion
from app.repositories.application import application_repo

@pytest.mark.asyncio
async def test_duplicate_recommendation_constraint(db_session):
    # Setup: Create necessary related records
    user = User(email="test_rec_dup@example.com", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    company = Company(name="Test Recommendation Corp", normalized_name="test recommendation corp")
    db_session.add(company)
    await db_session.flush()

    job = Job(
        title="Software Engineer",
        normalized_title="Software Engineer",
        description="Desc",
        location="Remote",
        job_type="Full-time",
        url="https://test.recommendations/safety/dup",
        company_id=company.id
    )
    db_session.add(job)
    await db_session.flush()

    resume = Resume(user_id=user.id, title="My Resume")
    db_session.add(resume)
    await db_session.flush()

    version = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        file_path="resumes/path.pdf",
        file_hash="hash",
        ocr_status="READY"
    )
    db_session.add(version)
    await db_session.flush()

    # Create the first recommendation
    rec1 = JobRecommendation(
        user_id=user.id,
        job_id=job.id,
        resume_version_id=version.id,
        score=85.0,
        explanation="First Explanation",
        is_saved=False,
        is_dismissed=False
    )
    db_session.add(rec1)
    await db_session.commit()

    # Attempt to create duplicate recommendation (same user, job, and version)
    rec2 = JobRecommendation(
        user_id=user.id,
        job_id=job.id,
        resume_version_id=version.id,
        score=90.0,
        explanation="Second Explanation",
        is_saved=False,
        is_dismissed=False
    )
    db_session.add(rec2)
    
    # Should throw IntegrityError/UniqueConstraint violation
    with pytest.raises(IntegrityError):
        await db_session.commit()
    
    await db_session.rollback()

@pytest.mark.asyncio
async def test_active_version_filtering(db_session):
    # Setup: Create necessary related records for a user with two resume versions
    user = User(email="test_version_filt@example.com", hashed_password="pw")
    db_session.add(user)
    await db_session.flush()

    company = Company(name="Test Recommendations Corp 2", normalized_name="test recommendations corp 2")
    db_session.add(company)
    await db_session.flush()

    job1 = Job(
        title="Python Engineer",
        normalized_title="Python Engineer",
        description="Desc",
        location="Remote",
        job_type="Full-time",
        url="https://test.recommendations/filt/1",
        company_id=company.id
    )
    job2 = Job(
        title="React Engineer",
        normalized_title="React Engineer",
        description="Desc",
        location="Remote",
        job_type="Full-time",
        url="https://test.recommendations/filt/2",
        company_id=company.id
    )
    db_session.add_all([job1, job2])
    await db_session.flush()

    resume = Resume(user_id=user.id, title="My Resume")
    db_session.add(resume)
    await db_session.flush()

    version1 = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        file_path="resumes/v1.pdf",
        file_hash="hash1",
        ocr_status="READY"
    )
    version2 = ResumeVersion(
        resume_id=resume.id,
        version_number=2,
        file_path="resumes/v2.pdf",
        file_hash="hash2",
        ocr_status="READY"
    )
    db_session.add_all([version1, version2])
    await db_session.flush()

    # Recommendations for version 1
    rec_v1 = JobRecommendation(
        user_id=user.id,
        job_id=job1.id,
        resume_version_id=version1.id,
        score=75.0,
        explanation="Version 1 Explanation",
        is_saved=False,
        is_dismissed=False
    )
    # Recommendations for version 2
    rec_v2 = JobRecommendation(
        user_id=user.id,
        job_id=job2.id,
        resume_version_id=version2.id,
        score=95.0,
        explanation="Version 2 Explanation",
        is_saved=False,
        is_dismissed=False
    )
    db_session.add_all([rec_v1, rec_v2])
    await db_session.commit()

    # Case 1: Fetch recommendations for version 1 explicitly
    recs_v1 = await application_repo.get_recommendations_by_user(db_session, user_id=user.id, resume_version_id=version1.id)
    assert len(recs_v1) == 1
    assert recs_v1[0].job_id == job1.id
    assert recs_v1[0].explanation == "Version 1 Explanation"

    # Case 2: Fetch recommendations for version 2 explicitly
    recs_v2 = await application_repo.get_recommendations_by_user(db_session, user_id=user.id, resume_version_id=version2.id)
    assert len(recs_v2) == 1
    assert recs_v2[0].job_id == job2.id
    assert recs_v2[0].explanation == "Version 2 Explanation"
