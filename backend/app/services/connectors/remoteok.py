import httpx
import datetime
import hashlib
from typing import List, Tuple
from app.services.connectors.base import BaseConnector, retry_on_http_failure
from app.schemas.schemas import RawJobData

class RemoteOKConnector(BaseConnector):
    """
    Ingestion connector for RemoteOK (remoteok.com/api).
    """

    def get_name(self) -> str:
        return "RemoteOK"

    @retry_on_http_failure(max_retries=3, initial_delay=0.5)
    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        url = "https://remoteok.com/api"
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
            if not isinstance(data, list) or len(data) <= 1:
                return []
            
            # First element is legal metadata, skip it
            raw_items = data[1:]
            jobs = []
            
            for item in raw_items[:limit]:
                # Extract official job ID, fallback to deterministic fingerprint if unavailable
                source_job_id = str(item.get("id")) if item.get("id") else None
                if not source_job_id:
                    # Generate deterministic fingerprint based on URL, company, and title
                    hash_input = f"{item.get('url', '')}-{item.get('company', '')}-{item.get('position', '')}".encode("utf-8")
                    source_job_id = "ro-" + hashlib.sha256(hash_input).hexdigest()[:12]

                # Extract date
                created_at = None
                date_val = item.get("date")
                if date_val:
                    try:
                        created_at = datetime.datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                    except ValueError:
                        try:
                            created_at = datetime.datetime.fromtimestamp(int(date_val), tz=datetime.timezone.utc)
                        except Exception:
                            created_at = datetime.datetime.now(datetime.timezone.utc)
                else:
                    created_at = datetime.datetime.now(datetime.timezone.utc)

                # Map to RawJobData
                job_data = RawJobData(
                    source_job_id=source_job_id,
                    title=item.get("position", "Untitled Position"),
                    company_name=item.get("company", "Unknown Company"),
                    description=item.get("description", ""),
                    location=item.get("location") or "Remote",
                    job_type="Full-time",
                    is_remote=True,
                    url=item.get("url", ""),
                    company_logo=item.get("company_logo"),
                    company_website=item.get("company_website"),
                    salary_min=float(item.get("salary_min")) if item.get("salary_min") else None,
                    salary_max=float(item.get("salary_max")) if item.get("salary_max") else None,
                    currency=item.get("currency", "USD"),
                    skills=item.get("tags") or [],
                    created_at=created_at
                )
                jobs.append(job_data)
            
            return jobs

    async def check_health(self) -> Tuple[bool, str]:
        url = "https://remoteok.com/api"
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
