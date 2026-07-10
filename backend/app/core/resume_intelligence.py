"""
Resume Intelligence Engine — Phase 2B
--------------------------------------
Deterministic scoring (no AI defaults, no magic 70.0 fallbacks).
All scores are either computed from evidence in the parsed JSON,
or explicitly returned as None with a machine-readable reason.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Skill Normalization Catalog
# ---------------------------------------------------------------------------
# Each entry: (canonical_name, set_of_aliases_lowercase)
_SKILL_CATALOG: List[Tuple[str, set]] = [
    ("Python",         {"python", "py", "python3", "python 3"}),
    ("JavaScript",     {"javascript", "js", "ecmascript", "es6", "es2015"}),
    ("TypeScript",     {"typescript", "ts"}),
    ("React",          {"react", "reactjs", "react.js"}),
    ("Next.js",        {"nextjs", "next.js", "next js"}),
    ("Node.js",        {"nodejs", "node.js", "node js", "node"}),
    ("FastAPI",        {"fastapi", "fast api"}),
    ("Django",         {"django"}),
    ("Flask",          {"flask"}),
    ("SQL",            {"sql", "structured query language"}),
    ("PostgreSQL",     {"postgresql", "postgres", "psql"}),
    ("MySQL",          {"mysql"}),
    ("MongoDB",        {"mongodb", "mongo"}),
    ("Redis",          {"redis"}),
    ("Docker",         {"docker"}),
    ("Kubernetes",     {"kubernetes", "k8s"}),
    ("AWS",            {"aws", "amazon web services", "amazon aws"}),
    ("GCP",            {"gcp", "google cloud", "google cloud platform"}),
    ("Azure",          {"azure", "microsoft azure"}),
    ("Git",            {"git", "github", "gitlab", "bitbucket"}),
    ("CI/CD",          {"ci/cd", "cicd", "github actions", "gitlab ci", "jenkins", "circleci"}),
    ("REST API",       {"rest", "restful", "rest api", "restful api"}),
    ("GraphQL",        {"graphql"}),
    ("Java",           {"java"}),
    ("C++",            {"c++", "cpp", "c plus plus"}),
    ("C#",             {"c#", "csharp", "c sharp"}),
    ("Go",             {"go", "golang"}),
    ("Rust",           {"rust"}),
    ("Machine Learning", {"machine learning", "ml", "deep learning", "dl"}),
    ("TensorFlow",     {"tensorflow", "tf"}),
    ("PyTorch",        {"pytorch", "torch"}),
    ("Pandas",         {"pandas"}),
    ("NumPy",          {"numpy"}),
    ("Scikit-learn",   {"scikit-learn", "sklearn", "scikit learn"}),
    ("Linux",          {"linux", "unix", "bash", "shell scripting"}),
    ("Agile",          {"agile", "scrum", "kanban", "jira"}),
    ("Figma",          {"figma"}),
    ("Tailwind CSS",   {"tailwind", "tailwindcss", "tailwind css"}),
]

def normalize_skill(raw: str) -> str:
    """Return canonical skill name for a raw skill string, or title-cased raw if unknown."""
    lowered = raw.strip().lower()
    for canonical, aliases in _SKILL_CATALOG:
        if lowered in aliases or lowered == canonical.lower():
            return canonical
    return raw.strip().title()


def normalize_skills_list(skills: List[Any]) -> List[Dict[str, Any]]:
    """
    Accept a list of strings or dicts.
    Returns normalized list of dicts: [{name, years_experience}]
    """
    normalized = []
    seen = set()
    for s in skills:
        if isinstance(s, str):
            raw_name, years = s, None
        elif isinstance(s, dict):
            raw_name = s.get("name") or s.get("skill") or ""
            years = s.get("years") or s.get("years_experience")
        else:
            continue

        if not raw_name:
            continue

        canonical = normalize_skill(raw_name)
        if canonical.lower() in seen:
            continue  # deduplicate
        seen.add(canonical.lower())

        normalized.append({
            "name": canonical,
            "years_experience": float(years) if years is not None else None,
        })
    return normalized


# ---------------------------------------------------------------------------
# Deterministic Quality Score (0–100)
# ---------------------------------------------------------------------------
# Weighted rubric — each section contributes a fixed max points.
# If a section is missing/empty, that weight is lost (not defaulted).

_QUALITY_RUBRIC = {
    "has_contact_signal":    5,   # email/phone mentioned in text or parsed_json
    "has_summary":           5,   # summary/objective field present
    "experience_count":     25,   # ≥2 entries = full; 1 = half
    "experience_bullets":   15,   # entries have description/achievements
    "education_present":    10,   # ≥1 education entry
    "skills_count":         20,   # ≥8 skills = full; ≥4 = half; <4 = quarter
    "projects_present":     10,   # ≥1 project
    "certifications":        5,   # ≥1 cert
    "quantified_impact":     5,   # numbers/% in experience descriptions
}

def _quality_score(parsed_json: Dict[str, Any], raw_text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Compute quality score 0–100 deterministically.
    Returns (score, None) on success or (None, reason) if data is unusable.
    """
    if not parsed_json and not raw_text:
        return None, "Both parsed_json and raw_text are empty — cannot score."

    experience = parsed_json.get("experience") or []
    education  = parsed_json.get("education") or []
    skills     = parsed_json.get("skills") or []
    projects   = parsed_json.get("projects") or []
    certs      = parsed_json.get("certifications") or []
    summary    = parsed_json.get("summary") or parsed_json.get("objective") or ""

    # Start with a base score of 10 to align with market average scoring
    points = 10.0

    # Contact signal — heuristic on raw text
    if re.search(r"[\w.\-+]+@[\w.\-]+\.[a-z]{2,}", raw_text, re.I):
        points += _QUALITY_RUBRIC["has_contact_signal"]

    # Summary / Objective
    if isinstance(summary, str) and len(summary.strip()) > 20:
        points += _QUALITY_RUBRIC["has_summary"]

    # Experience count
    exp_count = len(experience)
    if exp_count >= 2:
        points += _QUALITY_RUBRIC["experience_count"]
    elif exp_count == 1:
        points += _QUALITY_RUBRIC["experience_count"] * 0.6

    # Experience bullets / description richness
    desc_fields = ("description", "responsibilities", "achievements", "bullets")
    entries_with_desc = sum(
        1 for e in experience
        if isinstance(e, dict) and any(e.get(f) for f in desc_fields)
    )
    if experience:
        ratio = entries_with_desc / len(experience)
        points += _QUALITY_RUBRIC["experience_bullets"] * ratio

    # Education
    if len(education) >= 1:
        points += _QUALITY_RUBRIC["education_present"]

    # Skills count
    skill_count = len(skills)
    if skill_count >= 8:
        points += _QUALITY_RUBRIC["skills_count"]
    elif skill_count >= 4:
        points += _QUALITY_RUBRIC["skills_count"] * 0.6
    elif skill_count > 0:
        points += _QUALITY_RUBRIC["skills_count"] * 0.3

    # Projects
    if len(projects) >= 1:
        points += _QUALITY_RUBRIC["projects_present"]

    # Certifications
    if len(certs) >= 1:
        points += _QUALITY_RUBRIC["certifications"]

    # Quantified impact (numbers in experience descriptions)
    all_text = " ".join(
        str(e.get(f, ""))
        for e in experience if isinstance(e, dict)
        for f in desc_fields
    )
    has_numbers = bool(re.search(r"\b\d+[\d%x+]*\b", all_text))
    if has_numbers:
        points += _QUALITY_RUBRIC["quantified_impact"]

    return round(min(points, 100.0), 1), None


# ---------------------------------------------------------------------------
# Deterministic ATS Score (0–100)
# ---------------------------------------------------------------------------
_ATS_RUBRIC = {
    "no_tables_detected":       10,  # heuristic: low tab-delimited content
    "standard_section_headers": 20,  # common ATS-readable section names present
    "skills_section_present":   15,  # explicit skills section
    "dates_formatted":          10,  # dates detected in experience
    "email_present":            10,  # machine-readable email
    "no_special_chars_heavy":   10,  # not overloaded with bullets/symbols
    "word_count_adequate":      10,  # 300–900 words is ideal
    "job_title_clarity":        15,  # each experience has a title field
}

_STANDARD_HEADERS = {
    "experience", "work experience", "employment history",
    "education", "academic background",
    "skills", "technical skills", "core competencies",
    "projects", "personal projects", "key projects",
    "certifications", "awards", "summary", "objective",
    "publications", "volunteer",
}

def _ats_score(parsed_json: Dict[str, Any], raw_text: str) -> Tuple[Optional[float], Optional[str]]:
    if not parsed_json and not raw_text:
        return None, "Both parsed_json and raw_text are empty — cannot score."

    text_lower = raw_text.lower()
    words = raw_text.split()
    experience = parsed_json.get("experience") or []
    skills = parsed_json.get("skills") or []

    points = 0.0

    # No heavy tab/table usage (heuristic)
    tab_count = raw_text.count("\t")
    if tab_count < 10:
        points += _ATS_RUBRIC["no_tables_detected"]

    # Standard section headers present
    found_headers = sum(1 for h in _STANDARD_HEADERS if h in text_lower)
    header_ratio = min(found_headers / 4, 1.0)
    points += _ATS_RUBRIC["standard_section_headers"] * header_ratio

    # Skills section
    if skills:
        points += _ATS_RUBRIC["skills_section_present"]

    # Dates in experience — look for 4-digit years
    date_matches = re.findall(r"\b(19|20)\d{2}\b", raw_text)
    if len(date_matches) >= 2:
        points += _ATS_RUBRIC["dates_formatted"]

    # Email present
    if re.search(r"[\w.\-+]+@[\w.\-]+\.[a-z]{2,}", raw_text, re.I):
        points += _ATS_RUBRIC["email_present"]

    # Not overloaded with special chars
    special_count = len(re.findall(r"[★•◆▸▶→■□●]", raw_text))
    if special_count < 30:
        points += _ATS_RUBRIC["no_special_chars_heavy"]

    # Word count 300–900
    wc = len(words)
    if 300 <= wc <= 900:
        points += _ATS_RUBRIC["word_count_adequate"]
    elif 200 <= wc < 300 or 900 < wc <= 1200:
        points += _ATS_RUBRIC["word_count_adequate"] * 0.5

    # Job title clarity
    if experience:
        titled = sum(1 for e in experience if isinstance(e, dict) and e.get("title"))
        ratio = titled / len(experience)
        points += _ATS_RUBRIC["job_title_clarity"] * ratio

    # Apply a strictness multiplier (0.9) to simulate real-world ATS parse failures
    # This aligns the score more closely with industry standard tools like Enhancv.
    points = points * 0.9

    return round(min(points, 100.0), 1), None


# ---------------------------------------------------------------------------
# Improvement Suggestions (deterministic, evidence-based)
# ---------------------------------------------------------------------------
def _generate_suggestions(
    parsed_json: Dict[str, Any], raw_text: str, quality: Optional[float], ats: Optional[float]
) -> List[str]:
    suggestions = []

    experience = parsed_json.get("experience") or []
    education  = parsed_json.get("education") or []
    skills     = parsed_json.get("skills") or []
    certs      = parsed_json.get("certifications") or []
    summary    = parsed_json.get("summary") or parsed_json.get("objective") or ""

    # Missing contact email
    if not re.search(r"[\w.\-+]+@[\w.\-]+\.[a-z]{2,}", raw_text, re.I):
        suggestions.append("Add a professional email address — ATS systems require machine-readable contact details.")

    # Missing summary
    if not (isinstance(summary, str) and len(summary.strip()) > 20):
        suggestions.append("Add a 3–5 sentence professional summary at the top to give recruiters immediate context.")

    # Weak experience section
    if len(experience) == 0:
        suggestions.append("Work experience section is missing or could not be parsed. Ensure it uses standard section header 'Experience' or 'Work Experience'.")
    elif len(experience) < 2:
        suggestions.append("Only one work experience entry found. Add more roles or internships to demonstrate progression.")
    else:
        # Check for quantified impact
        desc_text = " ".join(
            str(e.get(f, ""))
            for e in experience if isinstance(e, dict)
            for f in ("description", "achievements", "responsibilities", "bullets")
        )
        if not re.search(r"\b\d+[\d%x+]*\b", desc_text):
            suggestions.append("Add quantified achievements (e.g., 'reduced load time by 40%', 'managed team of 6') — these dramatically improve ATS and recruiter scores.")

    # Few skills
    if len(skills) < 4:
        suggestions.append("Fewer than 4 skills detected. Expand your skills section with relevant technical and soft skills.")
    elif len(skills) < 8:
        suggestions.append("Fewer than 8 skills detected. Consider listing additional technologies, tools, and frameworks relevant to your target roles.")

    # No education
    if len(education) == 0:
        suggestions.append("Education section is missing or unparseable. Ensure it uses standard headers like 'Education' or 'Academic Background'.")

    # No certifications
    if len(certs) == 0:
        suggestions.append("No certifications found. Adding relevant certifications (AWS, GCP, PMP, etc.) can significantly boost ATS scores.")

    # ATS score low
    if ats is not None and ats < 60:
        suggestions.append("ATS readiness is below 60. Check for use of tables, text boxes, or graphics that prevent ATS parsing.")

    # Word count check
    wc = len(raw_text.split())
    if wc < 200:
        suggestions.append(f"Resume text is very short ({wc} words). Most ATS systems prefer 300–900 words for professional experience.")
    elif wc > 1200:
        suggestions.append(f"Resume is very long ({wc} words). Consider trimming to 1–2 pages for better ATS and recruiter readability.")

    return suggestions[:8]  # cap at 8 actionable items


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------
class IntelligenceResult:
    __slots__ = (
        "quality_score", "quality_score_reason",
        "ats_score", "ats_score_reason",
        "suggestions",
        "normalized_skills",
    )

    def __init__(
        self,
        quality_score: Optional[float],
        quality_score_reason: Optional[str],
        ats_score: Optional[float],
        ats_score_reason: Optional[str],
        suggestions: List[str],
        normalized_skills: List[Dict[str, Any]],
    ):
        self.quality_score = quality_score
        self.quality_score_reason = quality_score_reason
        self.ats_score = ats_score
        self.ats_score_reason = ats_score_reason
        self.suggestions = suggestions
        self.normalized_skills = normalized_skills


def run_intelligence(
    parsed_json: Dict[str, Any],
    raw_text: str,
    ai_skills: Optional[List[Any]] = None,
) -> IntelligenceResult:
    """
    Main entrypoint.  Computes all deterministic intelligence signals.

    Args:
        parsed_json: structured dict from AI resume parser (may be empty/partial)
        raw_text:    raw extracted text from PDF/DOCX
        ai_skills:   raw skill list from AI parser (used for normalization)
    """
    # Merge AI skills into parsed_json if provided separately
    if ai_skills is not None:
        parsed_json = {**parsed_json, "skills": ai_skills}

    quality_score, quality_reason = _quality_score(parsed_json, raw_text)
    ats_score,     ats_reason     = _ats_score(parsed_json, raw_text)

    suggestions = _generate_suggestions(parsed_json, raw_text, quality_score, ats_score)

    normalized = normalize_skills_list(parsed_json.get("skills") or [])

    return IntelligenceResult(
        quality_score=quality_score,
        quality_score_reason=quality_reason,
        ats_score=ats_score,
        ats_score_reason=ats_reason,
        suggestions=suggestions,
        normalized_skills=normalized,
    )
