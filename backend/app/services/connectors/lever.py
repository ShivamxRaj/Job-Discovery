import httpx
import datetime
from typing import List
from app.services.connectors.base import BaseConnector
from app.schemas.schemas import RawJobData
from app.core.config import settings

class LeverConnector(BaseConnector):
    """
    Ingestion connector for Lever Postings API.
    Iterates over a configured list of company boards.
    """

    def __init__(self):
        self.companies = settings.LEVER_COMPANIES

    def get_name(self) -> str:
        return "Lever"

    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        if not self.companies:
            return []

        jobs = []
        limit_per_company = max(1, limit // len(self.companies))
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for company in self.companies:
                url = f"https://api.lever.co/v0/postings/{company}"
                params = {"mode": "json"}
                
                try:
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        continue
                    
                    raw_items = response.json()
                    if not isinstance(raw_items, list):
                        continue
                    
                    for item in raw_items[:limit_per_company]:
                        categories = item.get("categories", {})
                        location_display = categories.get("location") or "Remote"
                        job_type = categories.get("commitment") or "Full-time"
                        
                        # Determine remote status
                        title = item.get("text", "")
                        is_remote = False
                        if "remote" in location_display.lower() or "remote" in title.lower():
                            is_remote = True

                        created_at = datetime.datetime.now(datetime.timezone.utc)
                        created_at_val = item.get("createdAt")
                        if created_at_val:
                            try:
                                # Lever returns javascript millisecond timestamp
                                created_at = datetime.datetime.fromtimestamp(created_at_val / 1000.0, tz=datetime.timezone.utc)
                            except Exception:
                                pass

                        job_data = RawJobData(
                            title=title or "Untitled Position",
                            company_name=company.capitalize(),
                            description=item.get("descriptionHtml") or item.get("description") or "",
                            location=location_display,
                            job_type=job_type,
                            is_remote=is_remote,
                            url=item.get("hostedUrl", ""),
                            company_logo=None,
                            company_website=None,
                            salary_min=None,
                            salary_max=None,
                            currency="USD",
                            skills=[categories.get("team"), categories.get("department")] if categories else [],
                            created_at=created_at
                        )
                        jobs.append(job_data)
                except Exception as e:
                    print(f"[{self.get_name()}] Error fetching jobs for {company}: {e}")
                    
        return jobs[:limit]

    async def check_health(self) -> bool:
        test_company = self.companies[0] if self.companies else "spotify"
        url = f"https://api.lever.co/v0/postings/{test_company}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code in [200, 404]
        except Exception:
            return False
