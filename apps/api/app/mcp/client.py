"""Robinhood Trading MCP client."""

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class RobinhoodMCPClient:
    """MCP client for Robinhood Agentic Trading.

    Phase 1: stub with configuration checks.
    Phase 3: full MCP tool calls (portfolio, quotes, order preview, place/cancel).
    """

    def __init__(self):
        self.url = settings.robinhood_mcp_url
        self.enabled = settings.robinhood_mcp_enabled

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    async def get_portfolio_snapshot(self) -> dict:
        if not self.is_configured:
            raise RuntimeError("Robinhood MCP URL not configured")
        logger.info("mcp_portfolio_snapshot", url=self.url[:30])
        # TODO: connect via MCP SDK and call portfolio tools
        return {"source": "robinhood_mcp", "status": "not_connected"}

    async def preview_order(self, order: dict) -> dict:
        logger.info("mcp_order_preview", ticker=order.get("ticker"))
        return {"status": "preview_stub", "order": order}

    async def place_order(self, order: dict, approved: bool = False) -> dict:
        if not approved:
            return {"status": "rejected", "reason": "Manual approval required"}
        logger.info("mcp_place_order", ticker=order.get("ticker"))
        return {"status": "placed_stub", "order": order}
