"""Portfolio endpoints — Robinhood MCP or demo data."""

from fastapi import APIRouter

from app.core.config import settings
from app.mcp.factory import get_mcp_client
from app.portfolio.demo import demo_portfolio

router = APIRouter()


@router.get("")
async def get_portfolio():
    if settings.robinhood_mcp_enabled:
        client = get_mcp_client()
        return await client.get_portfolio_snapshot()
    return demo_portfolio()
