import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.normalization_service import NormalizationService
from app.services.skill_service import SkillService
from app.services.deduplication_service import DeduplicationService
from app.services.job_service import JobService
from app.models.models import Job, Company, Skill

# 1. Test Parsers and Normalization in NormalizationService
def test_company_normalization():
    norm, orig = NormalizationService.normalize_company("Google LLC")
    assert norm == "Google"
    assert orig == "Google LLC"

    norm2, orig2 = NormalizationService.normalize_company("Amazon Inc")
    assert norm2 == "Amazon"

    norm3, orig3 = NormalizationService.normalize_company("HOREICH GmbH")
    assert norm3 == "Horeich"

def test_title_normalization():
    norm, orig, conf = NormalizationService.normalize_title("ReactJS Developer")
    assert norm == "React Developer"
    assert orig == "ReactJS Developer"

    norm2, orig2, conf2 = NormalizationService.normalize_title("Frontend Engineer")
    assert norm2 == "Frontend Developer"

    norm3, orig3, conf3 = NormalizationService.normalize_title("NodeJS Developer")
    assert norm3 == "Node.js Developer"

def test_employment_type_parsing():
    assert NormalizationService.parse_employment_type("Full Time") == "FULL_TIME"
    assert NormalizationService.parse_employment_type("Contractor") == "CONTRACT"
    assert NormalizationService.parse_employment_type("Internship") == "INTERN"
    assert NormalizationService.parse_employment_type("Freelance gig") == "FREELANCE"

def test_location_parsing():
    city, state, country, is_remote, remote_type, conf = NormalizationService.parse_location("Bangalore, Karnataka")
    assert city == "Bengaluru"
    assert state == "Karnataka"
    assert country == "India"
    assert is_remote is False
    assert remote_type == "Onsite"

    city2, state2, country2, is_remote2, remote_type2, conf2 = NormalizationService.parse_location("WFH")
    assert is_remote2 is True
    assert remote_type2 == "Remote"

def test_salary_parsing():
    # LPA format
    s_min, s_max, currency, period, conf = NormalizationService.parse_salary("₹15-20 LPA")
    assert s_min == 1500000.0
    assert s_max == 2000000.0
    assert currency == "INR"
    assert period == "yearly"

    # Dollar K format
    s_min2, s_max2, currency2, period2, conf2 = NormalizationService.parse_salary("$100k-$120k")
    assert s_min2 == 100000.0
    assert s_max2 == 120000.0
    assert currency2 == "USD"
    assert period2 == "yearly"

# 2. Test Skill Normalization & Mapping
@pytest.mark.asyncio
async def test_skill_normalization_and_aliases(db_session: AsyncSession):
    # Check Postgres -> PostgreSQL
    skill_obj = await SkillService.get_or_create_skill(db_session, "Postgres")
    assert skill_obj.name == "PostgreSQL"

    # Check ReactJS -> React
    skill_obj2 = await SkillService.get_or_create_skill(db_session, "ReactJS")
    assert skill_obj2.name == "React"

# 3. Test Deduplication logic
@pytest.mark.asyncio
async def test_cross_source_deduplication(db_session: AsyncSession):
    job_service = JobService()
    
    job_data_1 = {
        "title": "ReactJS Developer",
        "company_name": "Unique Tech LLC",
        "location": "Bangalore",
        "job_type": "Full-time",
        "url": "https://unique.com/job1",
        "description": "Building cool react apps.",
        "skills": ["ReactJS"]
    }
    
    # Ingest first job
    job1 = await job_service.ingest_job(db_session, job_data_1, "SourceA")
    assert job1.normalized_company_name == "Unique Tech"
    assert job1.normalized_title == "React Developer"
    assert job1.city == "Bengaluru"
    assert job1.duplicate_group_id is None
    
    job_data_2 = {
        "title": "React Developer",
        "company_name": "Unique Tech Inc",
        "location": "Bangalore, Karnataka",
        "job_type": "Full-time",
        "url": "https://unique.com/job2",
        "description": "Building cool react apps.",
        "skills": ["React"]
    }
    
    # Ingest strict duplicate
    job2 = await job_service.ingest_job(db_session, job_data_2, "SourceB")
    assert job2.duplicate_group_id is not None
    assert job2.duplicate_reason == "STRICT_MATCH"
    assert job2.is_active is False  # de-activated/auto-merged
    
    # Check false-positive prevention: same title but different city
    job_data_3 = {
        "title": "React Developer",
        "company_name": "Unique Tech Inc",
        "location": "Mumbai",
        "job_type": "Full-time",
        "url": "https://unique.com/job3",
        "description": "Building cool react apps.",
        "skills": ["React"]
    }
    job3 = await job_service.ingest_job(db_session, job_data_3, "SourceC")
    # Should not be strict match because cities differ (Bengaluru vs Mumbai)
    assert job3.duplicate_reason != "STRICT_MATCH"

# 4. Test Category Classification
def test_category_classification():
    # Solutions Architect ➔ SOFTWARE_ENGINEERING
    cat1, conf1 = NormalizationService.classify_category("Solutions Architect")
    assert cat1 == "SOFTWARE_ENGINEERING"
    
    # Technical Consultant ➔ SOFTWARE_ENGINEERING
    cat2, conf2 = NormalizationService.classify_category("Technical Consultant")
    assert cat2 == "SOFTWARE_ENGINEERING"
    
    # AI Product Consultant ➔ AI_ML
    cat3, conf3 = NormalizationService.classify_category("AI Product Consultant")
    assert cat3 == "AI_ML"
    
    # Technical Buyer ➔ FINANCE
    cat4, conf4 = NormalizationService.classify_category("Technical Buyer")
    assert cat4 == "FINANCE"
    
    # Security Program Manager ➔ CYBERSECURITY
    cat5, conf5 = NormalizationService.classify_category("Security Program Manager")
    assert cat5 == "CYBERSECURITY"

def test_granular_salary_confidence():
    # Exact salary
    _, _, _, _, conf1 = NormalizationService.parse_salary("$120,000")
    assert conf1 == 1.0
    
    # Partial salary
    _, _, _, _, conf2 = NormalizationService.parse_salary("Up to $150k")
    assert conf2 == 0.7
    
    # Salary with bonus
    _, _, _, _, conf3 = NormalizationService.parse_salary("$100k plus bonus and equity")
    assert conf3 == 0.8
    
    # Competitive / Negotiable
    _, _, _, _, conf4 = NormalizationService.parse_salary("Competitive salary")
    assert conf4 == 0.1
