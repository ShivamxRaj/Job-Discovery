import datetime
from typing import List, Optional, Any
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, Float, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base

# 1. Users Model
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    auth_accounts: Mapped[List["Auth"]] = relationship("Auth", back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[Optional["UserPreferences"]] = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    recommendations: Mapped[List["JobRecommendation"]] = relationship("JobRecommendation", back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    match_runs: Mapped[List["MatchRun"]] = relationship("MatchRun", back_populates="user", cascade="all, delete-orphan")


# 2. Auth (OAuth / Sessions) Model
class Auth(Base):
    __tablename__ = "auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # 'local', 'google', etc.
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="auth_accounts")


# 3. User Preferences Model
class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_locations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # List of strings
    preferred_job_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Full-time, Part-time, Internship
    preferred_roles: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)      # Software Engineer, Product Manager
    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    company_exclusions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Don't show these companies

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")


# 4. Resume Model
class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")
    versions: Mapped[List["ResumeVersion"]] = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")


# 5. Resume Versions Model
class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # 'READY' | 'PENDING_OCR' | 'OCR_FAILED'
    ocr_status: Mapped[str] = mapped_column(String(20), default="READY", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="versions")
    parsed_data: Mapped[Optional["ResumeParsedData"]] = relationship("ResumeParsedData", back_populates="resume_version", uselist=False, cascade="all, delete-orphan")
    skills: Mapped[List["ResumeSkill"]] = relationship("ResumeSkill", back_populates="resume_version", cascade="all, delete-orphan")
    projects: Mapped[List["ResumeProject"]] = relationship("ResumeProject", back_populates="resume_version", cascade="all, delete-orphan")
    certifications: Mapped[List["ResumeCertification"]] = relationship("ResumeCertification", back_populates="resume_version", cascade="all, delete-orphan")
    embedding: Mapped[Optional["ResumeEmbedding"]] = relationship("ResumeEmbedding", back_populates="resume_version", uselist=False, cascade="all, delete-orphan")
    recommendations: Mapped[List["JobRecommendation"]] = relationship("JobRecommendation", back_populates="resume_version", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="resume_version", cascade="all, delete-orphan")


# 6. Resume Parsed Data Model
class ResumeParsedData(Base):
    __tablename__ = "resume_parsed_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), unique=True, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Nullable scores — null = could not be computed deterministically
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_score_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ats_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ats_score_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    # Embedding metadata stored alongside vector
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="parsed_data")


# 7. Resume Skills Model
class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    years_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skill_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="skills")
    skill: Mapped[Optional["Skill"]] = relationship("Skill")


# 8. Resume Projects Model
class ResumeProject(Base):
    __tablename__ = "resume_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills_used: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Relationships
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="projects")


# 9. Resume Certifications Model
class ResumeCertification(Base):
    __tablename__ = "resume_certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime, nullable=True)

    # Relationships
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="certifications")


# 10. Resume Embeddings Model (pgvector)
class ResumeEmbedding(Base):
    __tablename__ = "resume_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), unique=True, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=False)  # OpenAI text-embedding-3-small (1536 dim)

    # Relationships
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="embedding")


# 11. Companies Model
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company")


class CanonicalCompany(Base):
    __tablename__ = "canonical_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    aliases: Mapped[List["CompanyAlias"]] = relationship("CompanyAlias", back_populates="company", cascade="all, delete-orphan")


class CompanyAlias(Base):
    __tablename__ = "company_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alias: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("canonical_companies.id", ondelete="CASCADE"), nullable=False)

    company: Mapped["CanonicalCompany"] = relationship("CanonicalCompany", back_populates="aliases")


# 12. Jobs Model
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    location: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # Full-time, Part-time, Internship, Contract
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_seed_data: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    data_origin: Mapped[str] = mapped_column(String(50), default="MANUAL", server_default="'MANUAL'", nullable=False)
    embedding_status: Mapped[str] = mapped_column(String(50), default="PENDING", server_default="'PENDING'", nullable=False, index=True)
    embedding_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    normalized_company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    remote_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    salary_period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duplicate_group_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    duplicate_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duplicate_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    normalization_version: Mapped[str] = mapped_column(String(50), default="v1", server_default="'v1'", nullable=False)
    title_confidence: Mapped[float] = mapped_column(Float, default=1.0, server_default="'1.0'", nullable=False)
    salary_confidence: Mapped[float] = mapped_column(Float, default=1.0, server_default="'1.0'", nullable=False)
    location_confidence: Mapped[float] = mapped_column(Float, default=1.0, server_default="'1.0'", nullable=False)
    job_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    category_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="jobs")
    source: Mapped[Optional["JobSource"]] = relationship("JobSource", back_populates="jobs")
    skills: Mapped[List["JobSkill"]] = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    embedding: Mapped[Optional["JobEmbedding"]] = relationship("JobEmbedding", back_populates="job", uselist=False, cascade="all, delete-orphan")
    recommendations: Mapped[List["JobRecommendation"]] = relationship("JobRecommendation", back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job", cascade="all, delete-orphan")


# 13. Job Sources Model
class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # RemoteOK, Arbeitnow, Adzuna, Greenhouse, Lever
    parser_type: Mapped[str] = mapped_column(String(50), nullable=False)  # JSON, RSS, HTML, API
    api_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="source")


# 14. Job Skills Model
class JobSkill(Base):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    skill_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="skills")
    skill: Mapped[Optional["Skill"]] = relationship("Skill")


# 14b. Skills Master Model
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)

    parent: Mapped[Optional["Skill"]] = relationship("Skill", remote_side=[id], backref="children")


# 14c. Skill Aliases Model
class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alias: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    skill: Mapped["Skill"] = relationship("Skill")


# 15. Job Embeddings Model (pgvector)
class JobEmbedding(Base):
    __tablename__ = "job_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=False)  # OpenAI text-embedding-3-small (1536 dim)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="embedding")


# 16. Duplicate Groups Model
class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    primary_job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    duplicate_job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("primary_job_id", "duplicate_job_id", name="uq_primary_duplicate_job"),
    )


# 17. Job Recommendations Model
class JobRecommendation(Base):
    __tablename__ = "job_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "resume_version_id", name="uq_user_job_resume_version"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recommendations")
    job: Mapped["Job"] = relationship("Job", back_populates="recommendations")
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="recommendations")


# 18. Applications Model
class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Applied")  # 'Applied', 'Interview', 'Rejected', 'Offer'
    cover_letter_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    hr_email_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion", back_populates="applications")


# 19. Notifications Model
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="alert")  # 'email', 'digest', 'alert'
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")


# 20. Audit Logs Model
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


# 21. Match Runs Model
class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resume_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Pending")  # 'Pending', 'Running', 'Completed', 'Failed'
    run_type: Mapped[str] = mapped_column(String(50), default="Manual")  # 'Manual', 'Auto'
    jobs_processed: Mapped[int] = mapped_column(Integer, default=0)
    matches_found: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="match_runs")


# 22. Scoring Config Model
class ScoringConfig(Base):
    __tablename__ = "scoring_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True) # None = global config
    skill_weight: Mapped[float] = mapped_column(Float, default=0.25)
    experience_weight: Mapped[float] = mapped_column(Float, default=0.20)
    education_weight: Mapped[float] = mapped_column(Float, default=0.10)
    location_weight: Mapped[float] = mapped_column(Float, default=0.15)
    remote_weight: Mapped[float] = mapped_column(Float, default=0.10)
    salary_weight: Mapped[float] = mapped_column(Float, default=0.10)
    freshness_weight: Mapped[float] = mapped_column(Float, default=0.10)


# 23. Cleanup Jobs Model
class CleanupJob(Base):
    __tablename__ = "cleanup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # 'PENDING', 'PROCESSING', 'SUCCESS', 'FAILED', 'PERMANENT_FAILURE'
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# 24. Raw Jobs Model (Ingestion Queue)
class RawJob(Base):
    __tablename__ = "raw_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_remote: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    company_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    company_website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), default="USD")
    skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)  # 'PENDING', 'PROCESSED', 'FAILED'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

