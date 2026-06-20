"""Production health and readiness probes."""

from fastapi import APIRouter

from app.core.config import settings
from app.core.health import readiness_report
from app.db.storage import get_storage
from app.mcp.factory import get_mcp_client

router = APIRouter()


@router.get("/ready")
async def readiness():
    report = await readiness_report()
    mcp = get_mcp_client()
    storage_backend = "unknown"
    try:
        storage = await get_storage()
        storage_backend = storage.backend_name
    except RuntimeError:
        storage_backend = "not_initialized"

    return {
        **report,
        "phase": 9,
        "push_notifications_enabled": settings.push_notifications_enabled,
        "audit_export_max_days": settings.audit_export_max_days,
        "platform_health_check_enabled": settings.platform_health_check_enabled,
        "multi_broker_enabled": settings.multi_broker_enabled,
        "options_workflow_enabled": settings.options_workflow_enabled,
        "tax_lot_tracking_enabled": settings.tax_lot_tracking_enabled,
        "news_provider": settings.active_news_provider,
        "regime_detection_enabled": settings.regime_detection_enabled,
        "sec_filings_enabled": settings.sec_filings_enabled,
        "storage_backend": storage_backend,
        "market_data_provider": settings.active_market_provider,
        "embedding_provider": settings.active_embedding_provider,
        "mcp_provider": settings.active_mcp_provider,
        "alert_provider": settings.active_alert_provider,
        "auth_enabled": settings.auth_enabled,
        "monitoring_enabled": settings.monitoring_enabled,
        "strategies_enabled": settings.strategies_enabled,
        "validation_gate_enabled": settings.validation_gate_enabled,
        "automation_feature_enabled": settings.automation_feature_enabled,
        "mcp_configured": mcp.is_configured,
        "mcp_enabled": settings.robinhood_mcp_enabled,
        "llm_configured": bool(
            settings.cursor_api_key or settings.openai_api_key or settings.anthropic_api_key
        ),
        "cursor_cloud_repo_set": bool(settings.cursor_cloud_repo_url),
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "polygon_key_set": bool(settings.polygon_api_key),
        "openai_key_set": bool(settings.openai_api_key),
        "slack_configured": settings.use_slack_alerts,
        "email_configured": settings.use_email_alerts,
    }
