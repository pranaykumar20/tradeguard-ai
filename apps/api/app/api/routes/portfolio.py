"""Portfolio endpoints — Robinhood MCP or demo data."""

from fastapi import APIRouter

from app.mcp.client import RobinhoodMCPClient
from app.portfolio.demo import demo_portfolio

router = APIRouter()


@router.get("")
async def get_portfolio():
    client = RobinhoodMCPClient()
    if client.is_configured and client.enabled:
        return await client.get_portfolio_snapshot()
    return demo_portfolio()
