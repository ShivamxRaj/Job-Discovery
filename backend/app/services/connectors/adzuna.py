import httpx
import datetime
from typing import List, Optional
from app.services.connectors.base import BaseConnector
from app.schemas.schemas import RawJobData
from app.core.config import settings

class AdzunaConnector(BaseConnector):
    """
    Ingestion connector for Adzuna (api.adzuna.com).
    Requires app_id and app_key.
    """

    def __init__(self):
        self.app_id = settings.ADZUNA_APP_ID
        self.app_key = settings.ADZUNA_APP_KEY
        self.country = "us" # default to US jobs

    def get_name(self) -> str:
        return "Adzuna"

    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        if not self.app_id or not self.app_key:
            print(f"[{self.get_name()}] Credentials not configured. Skipping.")
            return []

        url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": limit,
            "content-type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    return []
                
                data = response.json()
                raw_items = data.get("results", [])
                jobs = []
                
                for item in raw_items:
                    created_at_val = item.get("created")
                    if created_at_val:
                        try:
                            # Adzuna dates are e.g. 2026-07-01T20:45:00Z
                            created_at = datetime.datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
                        except Exception:
                            created_at = datetime.datetime.now(datetime.timezone.utc)
                    else:
                        created_at = datetime.datetime.now(datetime.timezone.utc)

                    # Determine remote status
                    is_remote = False
                    location_display = ""
                    location_obj = item.get("location")
                    if location_obj:
                        location_display = location_obj.get("display_name", "")
                    
                    title = item.get("title", "Untitled Position")
                    desc = item.get("description", "")
                    
                    if "remote" in location_display.lower() or "remote" in title.lower() or "work from home" in desc.lower():
                        is_remote = True

                    # Contract time map
                    contract_time = item.get("contract_time")
                    job_type = "Full-time"
                    if contract_time == "part_time":
                        job_type = "Part-time"
                    elif contract_time == "contract":
                        job_type = "Contract"

                    job_data = RawJobData(
                        title=title,
                        company_name=item.get("company", {}).get("display_name", "Unknown Company"),
                        description=desc,
                        location=location_display or "US",
                        job_type=job_type,
                        is_remote=is_remote,
                        url=item.get("redirect_url", ""),
                        company_logo=None,
                        company_website=None,
                        salary_min=item.get("salary_min"),
                        salary_max=item.get("salary_max"),
                        currency="USD",
                        skills=[item.get("category", {}).get("label")] if item.get("category") else [],
                        created_at=created_at
                    )
                    jobs.append(job_data)
                
                return jobs
        except Exception as e:
            print(f"[{self.get_name()}] Error fetching jobs: {e}")
            return []

    async def check_health(self) -> bool:
        if not self.app_id or not self.app_key:
            return False
        
        url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": 1,
            "content-type": "application/json"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params)
                return response.status_code in [200, 429]
        except Exception:
            return False
