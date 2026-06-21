"""Robinhood MCP client factory."""

from app.core.config import settings
from app.mcp.base import RobinhoodMCPClientBase
from app.mcp.live_client import LiveRobinhoodMCPClient
from app.mcp.mock_client import MockRobinhoodMCPClient


class UserAwareMCPClient(RobinhoodMCPClientBase):
    """Resolve mock vs live per request — user OAuth, global env, or demo mock."""

    provider_name = "auto"

    async def _resolve(self) -> RobinhoodMCPClientBase:
        from app.services.robinhood_connect import RobinhoodConnectService

        connect = RobinhoodConnectService()
        if await connect.is_user_connected():
            return LiveRobinhoodMCPClient()
        if settings.use_live_mcp:
            return LiveRobinhoodMCPClient(url=settings.robinhood_mcp_url or None)
        return MockRobinhoodMCPClient()

    @property
    def is_configured(self) -> bool:
        if settings.use_live_mcp:
            return True
        return settings.mcp_provider != "mock"

    async def get_portfolio_snapshot(self) -> dict:
        return await (await self._resolve()).get_portfolio_snapshot()

    async def get_quote(self, ticker: str) -> dict:
        return await (await self._resolve()).get_quote(ticker)

    async def preview_order(self, order: dict) -> dict:
        return await (await self._resolve()).preview_order(order)

    async def place_order(self, order: dict, approved: bool = False) -> dict:
        return await (await self._resolve()).place_order(order, approved=approved)

    async def cancel_order(self, order_id: str) -> dict:
        return await (await self._resolve()).cancel_order(order_id)


def get_mcp_client() -> RobinhoodMCPClientBase:
    if settings.mcp_provider == "mock":
        return MockRobinhoodMCPClient()
    return UserAwareMCPClient()


async def is_mcp_live_for_user() -> bool:
    from app.services.robinhood_connect import RobinhoodConnectService

    connect = RobinhoodConnectService()
    if await connect.is_user_connected():
        return True
    return settings.use_live_mcp


RobinhoodMCPClient = get_mcp_client
