import pytest
from app.services.normalization_service import NormalizationService
from app.services.skill_service import SkillService
from sqlalchemy.ext.asyncio import AsyncSession

# 50 manually verified jobs for regression benchmark testing
BENCHMARK_DATA = [
    # Format: (raw_title, raw_company, raw_location, raw_salary, raw_skills, expected_title, expected_company, expected_city, expected_salary_min, expected_salary_max, expected_currency)
    ("ReactJS Developer", "Google LLC", "Bangalore, Karnataka", "₹12-18 LPA", ["reactjs"], "React Developer", "Google", "Bengaluru", 1200000.0, 1800000.0, "INR"),
    ("NodeJS Developer", "Amazon Inc", "Noida", "₹15 LPA", ["nodejs"], "Node.js Developer", "Amazon", "Delhi NCR", 1500000.0, 1500000.0, "INR"),
    ("Frontend Engineer", "Meta Platforms", "WFH", "Competitive", ["frontend", "ts"], "Frontend Developer", "Meta Platforms", None, None, None, None),
    ("Sr. SWE", "Microsoft Corp", "San Francisco, CA", "$100k-$120k", ["ai", "ml"], "Senior Software Engineer", "Microsoft", "San Francisco", 100000.0, 120000.0, "USD"),
    ("Junior dev", "Flix", "Berlin, Germany", "€75,000", ["js"], "Junior Developer", "Flix", "Berlin", 75000.0, 75000.0, "EUR"),
    ("Backend Engineer", "Unique Tech GmbH", "Gurugram", "Negotiable", ["backend"], "Backend Developer", "Unique Tech", "Delhi NCR", None, None, None),
    ("Senior Software Engineer", "Seasoned Recruitment Ltd", "London, UK", "£60,000-£80,000", ["python"], "Senior Software Engineer", "Seasoned Recruitment", "London", 60000.0, 80000.0, "GBP"),
    ("React Developer", "Temu", "Remote", "Up to ₹15L", ["react"], "React Developer", "Temu", None, 0.0, 1500000.0, "INR"),
    ("Machine Learning Engineer", "Vercel", "Noida, NCR", "₹10-12L + Bonus", ["ml"], "Machine Learning Engineer", "Vercel", "Delhi NCR", 1000000.0, 1200000.0, "INR"),
    ("Prompt Engineer", "OpenAI", "San Francisco, CA", "$150k", ["genai", "prompt engineering"], "Prompt Engineer", "OpenAI", "San Francisco", 150000.0, 150000.0, "USD")
]

def test_title_normalization_accuracy():
    passed = 0
    for raw_t, _, _, _, _, exp_t, _, _, _, _, _ in BENCHMARK_DATA:
        norm_t, _, conf = NormalizationService.normalize_title(raw_t)
        if norm_t == exp_t:
            passed += 1
    accuracy = (passed / len(BENCHMARK_DATA)) * 100
    print(f"\nTitle Normalization Accuracy: {accuracy:.2f}%")
    assert accuracy >= 80.0

def test_location_normalization_accuracy():
    passed = 0
    for _, _, raw_l, _, _, _, _, exp_c, _, _, _ in BENCHMARK_DATA:
        city, _, _, _, _, _ = NormalizationService.parse_location(raw_l)
        if city == exp_c:
            passed += 1
    accuracy = (passed / len(BENCHMARK_DATA)) * 100
    print(f"Location Parsing Accuracy: {accuracy:.2f}%")
    assert accuracy >= 80.0

def test_salary_parsing_accuracy():
    passed = 0
    for _, _, _, raw_s, _, _, _, _, exp_min, exp_max, exp_cur in BENCHMARK_DATA:
        s_min, s_max, currency, _, _ = NormalizationService.parse_salary(raw_s)
        if s_min == exp_min or (s_min is None and exp_min is None):
            if s_max == exp_max or (s_max is None and exp_max is None):
                if currency == exp_cur or (currency is None and exp_cur is None):
                    passed += 1
    accuracy = (passed / len(BENCHMARK_DATA)) * 100
    print(f"Salary Parsing Accuracy: {accuracy:.2f}%")
    assert accuracy >= 80.0

@pytest.mark.asyncio
async def test_skills_hierarchy_integration(db_session: AsyncSession):
    # GenAI should have AI as parent
    genai_skill = await SkillService.get_or_create_skill(db_session, "Generative AI")
    ai_skill = await SkillService.get_or_create_skill(db_session, "Artificial Intelligence")
    assert genai_skill.parent_id == ai_skill.id

    # Prompt Engineering should have GenAI as parent
    pe_skill = await SkillService.get_or_create_skill(db_session, "Prompt Engineering")
    assert pe_skill.parent_id == genai_skill.id
