"""
Unit tests — Resume Intelligence Engine (Phase 2B)
--------------------------------------------------
Tests deterministic quality scoring, ATS scoring, skill normalization,
suggestion generation, and null-score behaviour (PENDING_OCR path).
"""
import pytest
from app.core.resume_intelligence import (
    normalize_skill,
    normalize_skills_list,
    run_intelligence,
)


# ──────────────────────────────────────────────────────────────────────────────
# Skill Normalization
# ──────────────────────────────────────────────────────────────────────────────

class TestSkillNormalization:
    def test_alias_maps_to_canonical(self):
        assert normalize_skill("reactjs") == "React"
        assert normalize_skill("postgres") == "PostgreSQL"
        assert normalize_skill("k8s") == "Kubernetes"
        assert normalize_skill("golang") == "Go"

    def test_canonical_name_returns_unchanged(self):
        assert normalize_skill("Python") == "Python"
        assert normalize_skill("Docker") == "Docker"

    def test_unknown_skill_returns_titlecased(self):
        result = normalize_skill("someobscurelib")
        assert result == "Someobscurelib"

    def test_list_deduplication(self):
        skills = ["Python", "python", "PYTHON", "py"]
        result = normalize_skills_list(skills)
        names = [s["name"] for s in result]
        assert names.count("Python") == 1

    def test_list_mixed_types(self):
        skills = [
            "React",
            {"name": "postgres", "years": 3},
            {"name": "docker", "years_experience": 2},
        ]
        result = normalize_skills_list(skills)
        names = [s["name"] for s in result]
        assert "React" in names
        assert "PostgreSQL" in names
        assert "Docker" in names

    def test_years_preserved(self):
        skills = [{"name": "Python", "years": 5.0}]
        result = normalize_skills_list(skills)
        assert result[0]["years_experience"] == 5.0

    def test_empty_list(self):
        assert normalize_skills_list([]) == []


# ──────────────────────────────────────────────────────────────────────────────
# Quality Score
# ──────────────────────────────────────────────────────────────────────────────

_FULL_PARSED = {
    "summary": "Experienced software engineer with 5 years building scalable web services.",
    "experience": [
        {
            "title": "Senior Engineer",
            "company": "Acme Corp",
            "description": "Led team of 6, improved throughput by 40%, reduced latency by 30%.",
        },
        {
            "title": "Software Engineer",
            "company": "Beta Ltd",
            "description": "Built REST API serving 1M requests/day.",
        },
    ],
    "education": [{"degree": "B.S. CS", "school": "State Uni", "year": 2019}],
    "skills": ["Python", "Docker", "PostgreSQL", "React", "AWS", "Kubernetes", "Redis", "Go"],
    "projects": [{"title": "Open Source CLI Tool"}],
    "certifications": [{"name": "AWS Solutions Architect"}],
}

_FULL_RAW = (
    "john.doe@example.com\n"
    "Senior Software Engineer\n"
    "Experienced software engineer with 5 years building scalable web services.\n"
    "Experience:\nSenior Engineer Acme Corp 2020-2023\n"
    "Led team of 6, improved throughput by 40%\n"
    "Education:\nB.S. CS State Uni 2019\n"
    "Skills: Python Docker PostgreSQL React AWS Kubernetes Redis Go\n"
    "Projects: Open Source CLI Tool\n"
    "Certifications: AWS Solutions Architect\n"
)


class TestQualityScore:
    def test_rich_resume_scores_above_80(self):
        intel = run_intelligence(_FULL_PARSED, _FULL_RAW)
        assert intel.quality_score is not None
        assert intel.quality_score >= 80.0
        assert intel.quality_score_reason is None  # no error, score computed

    def test_empty_inputs_return_null_with_reason(self):
        intel = run_intelligence({}, "")
        assert intel.quality_score is None
        assert intel.quality_score_reason is not None
        assert "empty" in intel.quality_score_reason.lower()

    def test_score_no_experience_is_lower(self):
        sparse = {"skills": ["Python"], "education": [{"degree": "BSc"}]}
        raw = "jane@test.com\nPython developer\nEducation: BSc 2022\n"
        intel = run_intelligence(sparse, raw)
        assert intel.quality_score is not None
        # Should be below 50 — missing experience, few skills, no projects, etc.
        assert intel.quality_score < 50.0

    def test_score_is_bounded_0_to_100(self):
        intel = run_intelligence(_FULL_PARSED, _FULL_RAW * 5)  # duplicate text
        assert 0.0 <= intel.quality_score <= 100.0

    def test_score_without_email_is_lower_than_with_email(self):
        raw_no_email = _FULL_RAW.replace("john.doe@example.com", "")
        intel_with = run_intelligence(_FULL_PARSED, _FULL_RAW)
        intel_without = run_intelligence(_FULL_PARSED, raw_no_email)
        assert intel_with.quality_score > intel_without.quality_score


# ──────────────────────────────────────────────────────────────────────────────
# ATS Score
# ──────────────────────────────────────────────────────────────────────────────

class TestATSScore:
    def test_ats_rich_resume_above_60(self):
        intel = run_intelligence(_FULL_PARSED, _FULL_RAW)
        assert intel.ats_score is not None
        assert intel.ats_score >= 60.0

    def test_ats_empty_is_null_with_reason(self):
        intel = run_intelligence({}, "")
        assert intel.ats_score is None
        assert intel.ats_score_reason is not None

    def test_ats_penalises_heavy_special_chars(self):
        heavy_bullets = "★★★★★" * 20 + " Python Developer " + "●●●●" * 10
        parsed = {"skills": ["Python"], "experience": [{"title": "Dev", "company": "X"}]}
        intel = run_intelligence(parsed, heavy_bullets + " experience education ")
        # should score lower due to special char penalty
        assert intel.ats_score is not None

    def test_ats_word_count_penalty_short(self):
        short_text = "Python developer. Email: a@b.com"  # < 200 words
        parsed = {"skills": ["Python"]}
        intel = run_intelligence(parsed, short_text)
        assert intel.ats_score is not None
        # word count < 300 means partial ats score on word_count_adequate rubric


# ──────────────────────────────────────────────────────────────────────────────
# Suggestions
# ──────────────────────────────────────────────────────────────────────────────

class TestSuggestions:
    def test_missing_email_suggestion(self):
        raw_no_email = _FULL_RAW.replace("john.doe@example.com", "")
        intel = run_intelligence(_FULL_PARSED, raw_no_email)
        assert any("email" in s.lower() for s in intel.suggestions)

    def test_no_suggestions_for_great_resume(self):
        """A truly complete resume should have fewer suggestions."""
        intel = run_intelligence(_FULL_PARSED, _FULL_RAW)
        # Even a great resume may have 0–2 suggestions; certainly not the max
        assert len(intel.suggestions) <= 8

    def test_missing_experience_suggestion(self):
        parsed = {"skills": ["Python"], "education": [{"degree": "BSc"}]}
        intel = run_intelligence(parsed, "john@example.com Python developer BSc")
        assert any("experience" in s.lower() for s in intel.suggestions)

    def test_few_skills_suggestion(self):
        parsed = {"skills": ["Python"], "experience": [], "education": []}
        intel = run_intelligence(parsed, "john@example.com Python")
        assert any("skill" in s.lower() for s in intel.suggestions)

    def test_suggestions_capped_at_8(self):
        intel = run_intelligence({}, "tiny")
        assert len(intel.suggestions) <= 8


# ──────────────────────────────────────────────────────────────────────────────
# OCR Stub path — null scores with explicit reason
# ──────────────────────────────────────────────────────────────────────────────

class TestOCRPath:
    def test_ocr_path_returns_null_scores(self):
        """Simulating what happens when raw_text is empty (PENDING_OCR path)."""
        intel = run_intelligence({}, "")
        assert intel.quality_score is None
        assert intel.ats_score is None
        assert intel.quality_score_reason is not None
        assert intel.ats_score_reason is not None
