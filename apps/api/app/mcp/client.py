"""Robinhood Trading MCP client — use get_mcp_client() from factory."""

from app.mcp.factory import RobinhoodMCPClient, get_mcp_client

__all__ = ["RobinhoodMCPClient", "get_mcp_client"]
