from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import datetime
import time

from app.services.connectors import connectors_registry
from app.models.models import RawJob
from app.schemas.schemas import RawJobData

class IngestionService:
    """
    Centralized service for managing raw job ingestion from multiple connectors.
    In Phase 3A, this service ONLY fetches raw data, maps it into RawJobData, and
    saves it to the `raw_jobs` table (the ingestion queue) without normalizing or embedding.
    """

    async def ingest_from_connector(self, db: AsyncSession, connector_name: str, limit: int = 15) -> Dict[str, Any]:
        """
        Trigger job ingestion from a single specific connector.
        Returns a sync summary dict (fetched, inserted, duplicates, duration_ms).
        """
        target_connector = None
        for c in connectors_registry:
            if c.get_name().lower() == connector_name.lower():
                target_connector = c
                break
        
        if not target_connector:
            raise ValueError(f"Unknown connector source: {connector_name}")
        
        start_time = time.perf_counter()
        name = target_connector.get_name()
        
        try:
            raw_jobs = await target_connector.fetch_jobs(limit=limit)
            added_count = 0
            duplicate_count = 0
            
            for rj in raw_jobs:
                # Deduplicate by URL in raw_jobs table to avoid duplicate queue items
                exists_query = select(RawJob.id).where(RawJob.url == rj.url)
                exists_res = await db.execute(exists_query)
                if exists_res.scalar_one_or_none() is not None:
                    duplicate_count += 1
                    continue
                
                # Create database record for the raw job
                raw_job_db = RawJob(
                    source=name,
                    source_job_id=rj.source_job_id,
                    url=rj.url,
                    title=rj.title,
                    company_name=rj.company_name,
                    description=rj.description,
                    location=rj.location,
                    job_type=rj.job_type,
                    is_remote=rj.is_remote,
                    company_logo=rj.company_logo,
                    company_website=rj.company_website,
                    salary_min=rj.salary_min,
                    salary_max=rj.salary_max,
                    currency=rj.currency or "USD",
                    skills=rj.skills or [],
                    status="PENDING"
                )
                db.add(raw_job_db)
                added_count += 1
            
            await db.commit()
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            return {
                "jobs_fetched": len(raw_jobs),
                "jobs_inserted": added_count,
                "duplicates": duplicate_count,
                "duration_ms": duration_ms
            }
        except Exception as e:
            await db.rollback()
            raise e

    async def ingest_from_all_connectors(self, db: AsyncSession, limit_per_connector: int = 15) -> Dict[str, Any]:
        """
        Trigger job ingestion from all registered connectors.
        Fills the raw_jobs queue while deduplicating by URL at the raw stage.
        """
        results = {}
        for connector in connectors_registry:
            name = connector.get_name()
            try:
                summary = await self.ingest_from_connector(db, name, limit_per_connector)
                results[name] = {
                    "status": "success",
                    "fetched": summary["jobs_fetched"],
                    "inserted": summary["jobs_inserted"],
                    "duplicates": summary["duplicates"],
                    "duration_ms": summary["duration_ms"]
                }
            except Exception as e:
                results[name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results

    async def check_connectors_health(self) -> Dict[str, Any]:
        """
        Perform a health check on all registered connectors.
        """
        overall_status = "healthy"
        connectors_health = {}
        
        for connector in connectors_registry:
            name = connector.get_name()
            try:
                is_healthy, message = await connector.check_health()
                connectors_health[name] = {
                    "healthy": is_healthy,
                    "status": "HEALTHY" if is_healthy else "UNHEALTHY",
                    "message": message
                }
                if not is_healthy:
                    overall_status = "degraded"
            except Exception as e:
                connectors_health[name] = {
                    "healthy": False,
                    "status": "UNHEALTHY",
                    "message": f"Unexpected health check crash: {str(e)}"
                }
                overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "connectors": connectors_health
        }

ingestion_service = IngestionService()
