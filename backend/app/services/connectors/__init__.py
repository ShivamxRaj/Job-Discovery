from app.services.connectors.remoteok import RemoteOKConnector
from app.services.connectors.arbeitnow import ArbeitnowConnector
from app.services.connectors.adzuna import AdzunaConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector

connectors_registry = [
    RemoteOKConnector(),
    ArbeitnowConnector(),
    AdzunaConnector(),
    GreenhouseConnector(),
    LeverConnector()
]
