import httpx
import datetime
from typing import List, Optional
from app.services.connectors.base import BaseConnector
from app.schemas.schemas import RawJobData

class RemoteOKConnector(BaseConnector):
    """
    Ingestion connector for RemoteOK (remoteok.com/api).
    """

    def get_name(self) -> str:
        return "RemoteOK"

    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        url = "https://remoteok.com/api"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return []
                
                data = response.json()
                if not isinstance(data, list) or len(data) <= 1:
                    return []
                
                # First element is legal metadata, skip it
                raw_items = data[1:]
                jobs = []
                
                for item in raw_items[:limit]:
                    # Extract date
                    created_at = None
                    date_val = item.get("date")
                    if date_val:
                        try:
                            # RemoteOK returns ISO format string (e.g. 2026-07-01T...)
                            created_at = datetime.datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        except ValueError:
                            # Try timestamp
                            try:
                                created_at = datetime.datetime.fromtimestamp(int(date_val), tz=datetime.timezone.utc)
                            except Exception:
                                created_at = datetime.datetime.now(datetime.timezone.utc)

                    # Determine remote status
                    is_remote = True # RemoteOK is remote-only
                    
                    # Map to RawJobData
                    job_data = RawJobData(
                        title=item.get("position", "Untitled Position"),
                        company_name=item.get("company", "Unknown Company"),
                        description=item.get("description", ""),
                        location=item.get("location") or "Remote",
                        job_type="Full-time", # Default for RemoteOK
                        is_remote=is_remote,
                        url=item.get("url", ""),
                        company_logo=item.get("company_logo"),
                        company_website=item.get("company_website"),
                        salary_min=item.get("salary_min"),
                        salary_max=item.get("salary_max"),
                        currency=item.get("currency", "USD"),
                        skills=item.get("tags") or [],
                        created_at=created_at or datetime.datetime.now(datetime.timezone.utc)
                    )
                    jobs.append(job_data)
                
                return jobs
        except Exception as e:
            # log or handle gracefully
            print(f"[{self.get_name()}] Error fetching jobs: {e}")
            return []

    async def check_health(self) -> bool:
        url = "https://remoteok.com/api"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                response = await client.get(url)
                # If we get a 200 or 429 (rate limited, but endpoint is active/correct), we consider it healthy/alive
                return response.status_code in [200, 429]
        except Exception:
            return False
