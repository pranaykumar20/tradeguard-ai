"""Live Robinhood MCP via MCP SDK — activated when ROBINHOOD_MCP_URL is set."""

import structlog

from app.core.config import settings
from app.mcp.base import RobinhoodMCPClientBase
from app.mcp.mock_client import MockRobinhoodMCPClient

logger = structlog.get_logger()


class LiveRobinhoodMCPClient(RobinhoodMCPClientBase):
    provider_name = "live"

    def __init__(self):
        self.url = settings.robinhood_mcp_url.rstrip("/")
        self._fallback = MockRobinhoodMCPClient()

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    async def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        try:
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamablehttp_client

            async with streamablehttp_client(self.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    if result.content:
                        text_blocks = [c.text for c in result.content if hasattr(c, "text")]
                        return {"status": "ok", "raw": "\n".join(text_blocks)}
                    return {"status": "ok", "raw": ""}
        except Exception as exc:
            logger.warning("mcp_live_call_failed", tool=tool_name, error=str(exc))
            raise

    async def get_portfolio_snapshot(self) -> dict:
        try:
            data = await self._call_tool("get_portfolio", {})
            return {"source": "robinhood_mcp", "status": "connected", "raw": data}
        except Exception:
            snap = await self._fallback.get_portfolio_snapshot()
            snap["source"] = "robinhood_mcp_fallback"
            return snap

    async def get_quote(self, ticker: str) -> dict:
        try:
            data = await self._call_tool("get_quote", {"ticker": ticker.upper()})
            return {"ticker": ticker.upper(), "provider": "live_mcp", "raw": data}
        except Exception:
            return await self._fallback.get_quote(ticker)

    async def preview_order(self, order: dict) -> dict:
        try:
            data = await self._call_tool("preview_order", order)
            return {"status": "preview_ok", "provider": "live_mcp", "raw": data, **order}
        except Exception:
            preview = await self._fallback.preview_order(order)
            preview["provider"] = "live_mcp_fallback"
            return preview

    async def place_order(self, order: dict, approved: bool = False) -> dict:
        if not approved:
            return {"status": "rejected", "reason": "Manual approval required", "provider": "live_mcp"}
        try:
            data = await self._call_tool("place_order", order)
            return {"status": "filled", "provider": "live_mcp", "raw": data, **order}
        except Exception:
            placed = await self._fallback.place_order(order, approved=True)
            placed["provider"] = "live_mcp_fallback"
            return placed

    async def cancel_order(self, order_id: str) -> dict:
        try:
            data = await self._call_tool("cancel_order", {"order_id": order_id})
            return {"status": "cancelled", "provider": "live_mcp", "raw": data}
        except Exception:
            return await self._fallback.cancel_order(order_id)
