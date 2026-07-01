from abc import ABC, abstractmethod
from typing import List
from app.schemas.schemas import RawJobData

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
    async def check_health(self) -> bool:
        """
        Perform a minimal network/service ping to determine if the API is reachable.
        Returns True if healthy, False otherwise.
        """
        pass
