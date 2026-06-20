"""Robinhood Agentic MCP — first live broker implementation."""

from app.brokers.base import BrokerAdapter
from app.mcp.factory import get_mcp_client


class RobinhoodMCPBroker(BrokerAdapter):
    broker_id = "robinhood_agentic"
    display_name = "Robinhood Agentic"

    def __init__(self):
        self._client = get_mcp_client()

    @property
    def provider_name(self) -> str:
        return self._client.provider_name

    @property
    def is_configured(self) -> bool:
        return self._client.is_configured

    async def get_portfolio_snapshot(self, account_id: str | None = None) -> dict:
        snap = await self._client.get_portfolio_snapshot()
        snap["broker_id"] = self.broker_id
        snap["account_id"] = account_id or "agentic-main"
        snap["account_label"] = "Robinhood Agentic"
        return snap

    async def get_quote(self, ticker: str) -> dict:
        return await self._client.get_quote(ticker)

    async def preview_order(self, order: dict) -> dict:
        preview = await self._client.preview_order(order)
        preview["broker_id"] = self.broker_id
        return preview

    async def place_order(self, order: dict, approved: bool = False) -> dict:
        result = await self._client.place_order(order, approved=approved)
        result["broker_id"] = self.broker_id
        return result

    async def cancel_order(self, order_id: str) -> dict:
        return await self._client.cancel_order(order_id)
