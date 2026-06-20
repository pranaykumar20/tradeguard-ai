"""Broker registry — resolve adapter by broker_id."""

from app.brokers.base import BrokerAdapter
from app.brokers.mock_ira import MockIRABroker
from app.brokers.robinhood_mcp import RobinhoodMCPBroker
from app.core.config import settings

_REGISTRY: dict[str, type[BrokerAdapter]] = {
    "robinhood_agentic": RobinhoodMCPBroker,
    "mock_ira": MockIRABroker,
}

_clients: dict[str, BrokerAdapter] = {}


def list_broker_ids() -> list[str]:
    ids = ["mock_ira"]
    if settings.robinhood_mcp_enabled:
        ids.insert(0, "robinhood_agentic")
    return ids


def get_broker(broker_id: str | None = None) -> BrokerAdapter:
    available = list_broker_ids()
    bid = broker_id or settings.default_broker_id
    if bid not in available:
        bid = available[0]
    if bid not in _clients:
        _clients[bid] = _REGISTRY[bid]()
    return _clients[bid]


def list_brokers() -> list[dict]:
    out = []
    for broker_id in list_broker_ids():
        broker = get_broker(broker_id)
        out.append(
            {
                "broker_id": broker_id,
                "display_name": broker.display_name,
                "configured": broker.is_configured,
            }
        )
    return out
