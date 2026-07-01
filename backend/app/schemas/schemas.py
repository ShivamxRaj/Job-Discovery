from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field
import datetime

# --- AUTH & USER ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

class GoogleLogin(BaseModel):
    credential: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class EmailVerifyRequest(BaseModel):
    token: str

class LogoutRequest(BaseModel):
    refresh_token: str

# --- PREFERENCES ---

class UserPreferencesUpdate(BaseModel):
    preferred_locations: Optional[List[str]] = None
    preferred_job_types: Optional[List[str]] = None
    preferred_roles: Optional[List[str]] = None
    min_salary: Optional[float] = None
    is_remote: Optional[bool] = None
    company_exclusions: Optional[List[str]] = None

class UserPreferencesResponse(BaseModel):
    id: int
    user_id: int
    preferred_locations: Optional[List[str]] = None
    preferred_job_types: Optional[List[str]] = None
    preferred_roles: Optional[List[str]] = None
    min_salary: Optional[float] = None
    is_remote: bool
    company_exclusions: Optional[List[str]] = None

    class Config:
        from_attributes = True

# --- RESUME ---

class ResumeResponse(BaseModel):
    id: int
    user_id: int
    title: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class ResumeSkillSchema(BaseModel):
    skill_name: str
    years_experience: Optional[float] = None

class ResumeProjectSchema(BaseModel):
    title: str
    description: Optional[str] = None
    skills_used: Optional[List[str]] = None

class ResumeCertificationSchema(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    issue_date: Optional[datetime.datetime] = None

class ResumeParsedDataResponse(BaseModel):
    # Scores are Optional — null means score could not be computed; check *_reason
    quality_score: Optional[float] = None
    quality_score_reason: Optional[str] = None
    ats_score: Optional[float] = None
    ats_score_reason: Optional[str] = None
    suggestions: List[str] = []
    parsed_json: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class EmbeddingMetadataResponse(BaseModel):
    model: str
    dimensions: int
    is_non_null: bool
    is_non_zero: bool
    sample_values: List[float]  # first 5 values for verification


class ResumeVersionResponse(BaseModel):
    id: int
    resume_id: int
    version_number: int
    file_path: str
    # 'READY' | 'PENDING_OCR' | 'OCR_FAILED'
    ocr_status: str = "READY"
    created_at: datetime.datetime
    parsed_data: Optional[ResumeParsedDataResponse] = None
    skills: List[ResumeSkillSchema] = []
    projects: List[ResumeProjectSchema] = []
    certifications: List[ResumeCertificationSchema] = []

    class Config:
        from_attributes = True

# --- JOBS ---

class CompanyResponse(BaseModel):
    id: int
    name: str
    normalized_name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True

class JobSkillResponse(BaseModel):
    skill_name: str

    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    id: int
    title: str
    normalized_title: str
    description: str
    company: CompanyResponse
    location: str
    job_type: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str
    is_remote: bool
    url: str
    created_at: datetime.datetime
    skills: List[JobSkillResponse] = []

    class Config:
        from_attributes = True

# --- MATCHING & RECOMMENDATIONS ---

class JobRecommendationResponse(BaseModel):
    id: int
    job_id: int
    score: float
    explanation: str
    is_saved: bool
    job: JobResponse

    class Config:
        from_attributes = True

# --- APPLICATIONS ---

class ApplicationCreate(BaseModel):
    job_id: int
    resume_version_id: int
    status: str = "Applied"
    notes: Optional[str] = None

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    resume_version_id: int
    status: str
    cover_letter_path: Optional[str] = None
    hr_email_text: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    job: JobResponse

    class Config:
        from_attributes = True

# --- AI GENERATIONS ---

class CoverLetterGenerateRequest(BaseModel):
    job_id: int
    resume_version_id: int

class AICoverLetterResponse(BaseModel):
    cover_letter: str

class AIHREmailResponse(BaseModel):
    hr_email: str

# --- NOTIFICATIONS ---

class NotificationResponse(BaseModel):
    id: int
    title: str
    content: str
    type: str
    is_read: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# --- INGESTION CONNECTORS ---

class RawJobData(BaseModel):
    """
    Intermediate schema representing raw job postings before normalization/deduplication.
    All connectors MUST map their API responses into this schema.
    """
    source_job_id: Optional[str] = Field(None, description="Unique job ID from the source board")
    title: str = Field(..., description="Raw position/job title")
    company_name: str = Field(..., description="Raw company name")
    description: str = Field(..., description="Raw job description (HTML or plain text)")
    location: Optional[str] = Field(None, description="Raw location string")
    job_type: Optional[str] = Field(None, description="Raw job type (e.g. Full-time, Contract, etc.)")
    is_remote: Optional[bool] = Field(None, description="Whether the job is remote")
    url: str = Field(..., description="Direct link to the job posting/source")
    company_logo: Optional[str] = Field(None, description="URL of company logo")
    company_website: Optional[str] = Field(None, description="URL of company website")
    salary_min: Optional[float] = Field(None, description="Minimum salary")
    salary_max: Optional[float] = Field(None, description="Maximum salary")
    currency: Optional[str] = Field("USD", description="Currency of salary")
    skills: Optional[List[str]] = Field(default_factory=list, description="Tags or skills mentioned")
    created_at: Optional[datetime.datetime] = Field(None, description="Job creation date/time")

