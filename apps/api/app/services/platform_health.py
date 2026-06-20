"""Platform health — MCP latency, readiness, model drift alerts."""

import time
from datetime import datetime, timezone

import structlog

from app.core.config import settings
from app.core.health import readiness_report
from app.db.storage import get_storage
from app.mcp.factory import get_mcp_client
from app.services.ml_retrain import MLRetrainService
from app.services.monitoring import MonitoringService

logger = structlog.get_logger()


class PlatformHealthService:
    def __init__(self):
        self.monitoring = MonitoringService()
        self.ml = MLRetrainService()

    async def check(self, *, emit_alerts: bool = True) -> dict:
        readiness = await readiness_report()
        mcp_latency_ms: float | None = None
        mcp_ok = True
        mcp_error: str | None = None

        if settings.robinhood_mcp_enabled:
            start = time.perf_counter()
            try:
                client = get_mcp_client()
                await client.get_quote("NVDA")
                mcp_latency_ms = round((time.perf_counter() - start) * 1000, 1)
            except Exception as exc:
                mcp_ok = False
                mcp_error = str(exc)
                if emit_alerts:
                    await self.monitoring.emit_alert(
                        event_type="platform_mcp_failure",
                        severity="high",
                        title="Platform: MCP Unreachable",
                        detail=str(exc),
                    )

        ml_status = await self.ml.status()
        current_accuracy = ml_status.get("accuracy")
        baseline = await self._baseline_accuracy()
        drift: float | None = None
        drift_alert = False

        if baseline is not None and current_accuracy is not None:
            drift = round(float(baseline) - float(current_accuracy), 4)
            if drift >= settings.model_drift_threshold:
                drift_alert = True
                if emit_alerts:
                    await self.monitoring.emit_alert(
                        event_type="model_drift",
                        severity="medium",
                        title="Platform: Model Accuracy Drift",
                        detail=(
                            f"Accuracy dropped {drift:.2%} from baseline "
                            f"({baseline:.2%} → {current_accuracy:.2%})"
                        ),
                    )

        latency_alert = (
            mcp_latency_ms is not None and mcp_latency_ms > settings.platform_latency_threshold_ms
        )
        if latency_alert and emit_alerts:
            await self.monitoring.emit_alert(
                event_type="platform_latency",
                severity="medium",
                title="Platform: MCP Latency High",
                detail=f"MCP quote latency {mcp_latency_ms:.0f}ms exceeds {settings.platform_latency_threshold_ms}ms",
            )

        result = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "readiness": readiness,
            "mcp": {
                "enabled": settings.robinhood_mcp_enabled,
                "ok": mcp_ok,
                "latency_ms": mcp_latency_ms,
                "error": mcp_error,
                "latency_alert": latency_alert,
            },
            "model": {
                **ml_status,
                "baseline_accuracy": baseline,
                "drift": drift,
                "drift_alert": drift_alert,
            },
            "thresholds": {
                "latency_ms": settings.platform_latency_threshold_ms,
                "model_drift": settings.model_drift_threshold,
            },
            "healthy": readiness.get("status") == "ready" and mcp_ok and not drift_alert and not latency_alert,
        }

        try:
            storage = await get_storage()
            await storage.set_app_state("platform_health", result)
        except RuntimeError:
            pass

        return result

    async def latest(self) -> dict:
        try:
            storage = await get_storage()
            cached = await storage.get_app_state("platform_health")
            if cached:
                return cached
        except RuntimeError:
            pass
        return await self.check(emit_alerts=False)

    async def _baseline_accuracy(self) -> float | None:
        try:
            storage = await get_storage()
            state = await storage.get_app_state("model_baseline")
            if state and state.get("accuracy") is not None:
                return float(state["accuracy"])
        except RuntimeError:
            pass
        ml_status = await self.ml.status()
        accuracy = ml_status.get("accuracy")
        if accuracy is not None:
            try:
                storage = await get_storage()
                await storage.set_app_state("model_baseline", {"accuracy": accuracy})
            except RuntimeError:
                pass
        return float(accuracy) if accuracy is not None else None
