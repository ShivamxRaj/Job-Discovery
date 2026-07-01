from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine, get_db
from app.db.base_class import Base
from app.models.models import *  # import all models to register with Declarative Base

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade AI-powered Job Discovery SaaS API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Logging & Performance middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"Method: {request.method} Path: {request.url.path} "
        f"Status: {response.status_code} Duration: {duration:.4f}s"
    )
    return response

# Startup database initialization
@app.on_event("startup")
async def startup_db_init():
    async with engine.begin() as conn:
        # Create pgvector extension if not exists (PostgreSQL only)
        if engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas initialized.")

# Import Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.applications import router as applications_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.admin import router as admin_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(resumes_router, prefix="/api/v1/resumes", tags=["resumes"])
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(applications_router, prefix="/api/v1/applications", tags=["applications"])
app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "status": "healthy",
        "version": "1.0.0"
    }
