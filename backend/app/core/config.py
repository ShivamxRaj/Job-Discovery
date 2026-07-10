import os
from typing import List, Optional
from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "../../.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    APP_NAME: str = "AI Job Discovery SaaS"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000",
        "https://job-discovery-six.vercel.app",
        "*"
    ]

    # Security & Auth
    SECRET_KEY: str = "production-grade-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # PostgreSQL Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/jobdiscovery"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Supabase Storage
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_BUCKET_NAME: str = "resumes"

    # OpenAI API
    OPENAI_API_KEY: Optional[str] = None

    # Job Connectors Settings
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None
    
    # Configurable company job boards list for Greenhouse and Lever V1
    GREENHOUSE_COMPANIES: List[str] = ["figma", "stripe", "openai", "cloudflare", "lever"]
    LEVER_COMPANIES: List[str] = ["spotify", "outreach"]

    # n8n Webhook Settings
    N8N_WEBHOOK_SECRET: Optional[str] = None

    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: str = "JobDiscovery AI"

    # Digest Schedules
    DAILY_DIGEST_HOUR: int = 8
    DAILY_DIGEST_MINUTE: int = 0
    WEEKLY_DIGEST_HOUR: int = 8
    WEEKLY_DIGEST_MINUTE: int = 0
    WEEKLY_DIGEST_DAY_OF_WEEK: str = "1" # 1 = Monday

    # Deduplication thresholds
    DEDUP_FUZZY_THRESHOLD_MIN: float = 0.78
    DEDUP_FUZZY_THRESHOLD_HIGH: float = 0.95
    DEDUP_SEMANTIC_THRESHOLD: float = 0.88


    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

settings = Settings()
