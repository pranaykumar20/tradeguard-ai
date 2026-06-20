"""Health check routes."""

from fastapi import APIRouter

from app.core.config import settings
from app.mcp.client import RobinhoodMCPClient

router = APIRouter()


@router.get("/ready")
async def readiness():
    mcp = RobinhoodMCPClient()
    return {
        "status": "ready",
        "mcp_configured": mcp.is_configured,
        "mcp_enabled": settings.robinhood_mcp_enabled,
        "llm_configured": bool(settings.openai_api_key or settings.anthropic_api_key),
    }
