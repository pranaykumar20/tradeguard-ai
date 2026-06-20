"""Health check routes."""

from fastapi import APIRouter

from app.core.config import settings
from app.db.storage import get_storage
from app.mcp.factory import get_mcp_client

router = APIRouter()


@router.get("/ready")
async def readiness():
    mcp = get_mcp_client()
    storage_backend = "unknown"
    try:
        storage = await get_storage()
        storage_backend = storage.backend_name
    except RuntimeError:
        storage_backend = "not_initialized"

    return {
        "status": "ready",
        "phase": 3,
        "storage_backend": storage_backend,
        "market_data_provider": settings.active_market_provider,
        "embedding_provider": settings.active_embedding_provider,
        "mcp_provider": settings.active_mcp_provider,
        "mcp_configured": mcp.is_configured,
        "mcp_enabled": settings.robinhood_mcp_enabled,
        "llm_configured": bool(settings.openai_api_key or settings.anthropic_api_key),
        "polygon_key_set": bool(settings.polygon_api_key),
        "openai_key_set": bool(settings.openai_api_key),
    }
