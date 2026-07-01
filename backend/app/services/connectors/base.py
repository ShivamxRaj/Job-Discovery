from abc import ABC, abstractmethod
from typing import List, Tuple
import asyncio
import logging
from app.schemas.schemas import RawJobData

logger = logging.getLogger(__name__)

def retry_on_http_failure(max_retries: int = 3, initial_delay: float = 0.5):
    """
    Decorator to retry async connector calls on exceptions with exponential backoff.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            connector_name = args[0].get_name() if args else "Connector"
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        logger.error(f"[{connector_name}] Fetch failed. Max retries exceeded. Exception: {exc}")
                        raise last_exc
                    logger.warning(
                        f"[{connector_name}] Fetch failed: {exc}. "
                        f"Retrying in {delay}s... (Retry {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
        return wrapper
    return decorator


class BaseConnector(ABC):
    """
    Abstract Base Class for all Job Ingestion Connectors.
    Connectors are ONLY responsible for fetching raw jobs, mapping them into RawJobData,
    and verifying API health. Normalization/embedding logic is centralized in Phase 3B.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the unique name of this connector."""
        pass

    @abstractmethod
    async def fetch_jobs(self, limit: int = 15) -> List[RawJobData]:
        """
        Fetch raw jobs from the target API and map them to RawJobData.
        Should handle pagination and limit.
        """
        pass

    @abstractmethod
    async def check_health(self) -> Tuple[bool, str]:
        """
        Perform a minimal network/service ping to determine if the API is reachable.
        Returns a tuple of (is_healthy, status_message_or_error).
        """
        pass
