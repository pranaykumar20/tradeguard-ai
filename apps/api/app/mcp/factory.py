"""Robinhood MCP client factory."""

from app.core.config import settings
from app.mcp.base import RobinhoodMCPClientBase
from app.mcp.live_client import LiveRobinhoodMCPClient
from app.mcp.mock_client import MockRobinhoodMCPClient

_client: RobinhoodMCPClientBase | None = None


def get_mcp_client() -> RobinhoodMCPClientBase:
    global _client
    if _client is None:
        if settings.use_live_mcp:
            _client = LiveRobinhoodMCPClient()
        else:
            _client = MockRobinhoodMCPClient()
    return _client


# Backwards-compatible alias
RobinhoodMCPClient = get_mcp_client
