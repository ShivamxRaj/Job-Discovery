import httpx
import datetime
from typing import List, Tuple
from app.services.connectors.base import BaseConnector, retry_on_http_failure
from app.schemas.schemas import RawJobData
from app.core.config import settings

class GreenhouseConnector(BaseConnector):
    """
    Ingestion connector for Greenhouse Boards API.
    Iterates over a configured list of company boards.
    """

    def __init__(self):
        self.companies = settings.GREENHOUSE_COMPANIES

    def get_name(self) -> str:
        return "Greenhouse"

    @retry_on_http_failure(max_retries=3, initial_delay=0.5)
    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        if not self.companies:
            return []

        jobs = []
        limit_per_company = max(1, limit // len(self.companies))
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for company in self.companies:
                url = f"https://board-api.greenhouse.io/v1/boards/{company}/jobs"
                params = {"content": "true"}
                
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    # Propagate HTTP error to trigger retry decorator if appropriate, or print and continue
                    print(f"[{self.get_name()}] Error board {company} returned status: {response.status_code}")
                    continue
                
                data = response.json()
                raw_items = data.get("jobs", [])
                
                for item in raw_items[:limit_per_company]:
                    location_display = "Remote"
                    location_obj = item.get("location")
                    if location_obj and isinstance(location_obj, dict):
                        location_display = location_obj.get("name") or "Remote"

                    title = item.get("title", "")
                    is_remote = False
                    if "remote" in location_display.lower() or "remote" in title.lower():
                        is_remote = True

                    created_at = datetime.datetime.now(datetime.timezone.utc)
                    updated_at_val = item.get("updated_at")
                    if updated_at_val:
                        try:
                            created_at = datetime.datetime.fromisoformat(updated_at_val.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    job_data = RawJobData(
                        source_job_id=str(item.get("id")) if item.get("id") else None,
                        title=title or "Untitled Position",
                        company_name=company.capitalize(),
                        description=item.get("content", ""),
                        location=location_display,
                        job_type="Full-time",
                        is_remote=is_remote,
                        url=item.get("absolute_url", ""),
                        company_logo=None,
                        company_website=None,
                        salary_min=None,
                        salary_max=None,
                        currency="USD",
                        skills=[],
                        created_at=created_at
                    )
                    jobs.append(job_data)
                    
        return jobs[:limit]

    async def check_health(self) -> Tuple[bool, str]:
        test_company = self.companies[0] if self.companies else "stripe"
        url = f"https://board-api.greenhouse.io/v1/boards/{test_company}/jobs"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code in [200, 404]:
                    return True, "Healthy"
                else:
                    return False, f"Unexpected HTTP status {response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
