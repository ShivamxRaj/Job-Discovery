import httpx
import datetime
from typing import List, Tuple
from app.services.connectors.base import BaseConnector, retry_on_http_failure
from app.schemas.schemas import RawJobData

class ArbeitnowConnector(BaseConnector):
    """
    Ingestion connector for Arbeitnow (arbeitnow.com/api/job-board-api).
    """

    def get_name(self) -> str:
        return "Arbeitnow"

    @retry_on_http_failure(max_retries=3, initial_delay=0.5)
    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Unexpected status code: {response.status_code}",
                    request=response.request,
                    response=response
                )
            
            data = response.json()
            raw_items = data.get("data", [])
            jobs = []
            
            for item in raw_items[:limit]:
                job_types = item.get("job_types", [])
                job_type = job_types[0] if job_types else "Full-time"
                
                created_at_val = item.get("created_at")
                if created_at_val:
                    try:
                        if isinstance(created_at_val, int):
                            created_at = datetime.datetime.fromtimestamp(created_at_val, tz=datetime.timezone.utc)
                        else:
                            created_at = datetime.datetime.fromtimestamp(int(created_at_val), tz=datetime.timezone.utc)
                    except Exception:
                        created_at = datetime.datetime.now(datetime.timezone.utc)
                else:
                    created_at = datetime.datetime.now(datetime.timezone.utc)

                # Map to RawJobData
                job_data = RawJobData(
                    source_job_id=item.get("slug"), # slug is unique identifier for Arbeitnow
                    title=item.get("title", "Untitled Position"),
                    company_name=item.get("company_name", "Unknown Company"),
                    description=item.get("description", ""),
                    location=item.get("location") or "Germany",
                    job_type=job_type,
                    is_remote=item.get("remote", False),
                    url=item.get("url", ""),
                    company_logo=None,
                    company_website=None,
                    salary_min=None,
                    salary_max=None,
                    currency="EUR",
                    skills=item.get("tags") or [],
                    created_at=created_at
                )
                jobs.append(job_data)
            
            return jobs

    async def check_health(self) -> Tuple[bool, str]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return True, "Healthy"
                elif response.status_code == 429:
                    return True, "Rate limited but reachable (429)"
                else:
                    return False, f"Unexpected HTTP status {response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
