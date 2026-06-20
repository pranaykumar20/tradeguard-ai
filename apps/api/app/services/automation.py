"""Phase 4.4 constrained automation — master switch, caps, audit trail."""

from datetime import datetime, timezone

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.services.monitoring import MonitoringService
from app.services.validation import ValidationService

logger = structlog.get_logger()

DEFAULT_AUTOMATION_STATE = {
    "enabled": False,
    "enabled_at": None,
    "disabled_at": None,
    "disabled_reason": "",
    "auto_trades_today": 0,
    "last_reset_date": None,
}


class AutomationService:
    def __init__(self):
        self.monitoring = MonitoringService()
        self.validation = ValidationService()

    async def _get_state(self) -> dict:
        try:
            storage = await get_storage()
            state = await storage.get_app_state("automation")
        except RuntimeError:
            return dict(DEFAULT_AUTOMATION_STATE)
        return {**DEFAULT_AUTOMATION_STATE, **(state or {})}

    async def _save_state(self, state: dict) -> dict:
        try:
            storage = await get_storage()
            await storage.set_app_state("automation", state)
        except RuntimeError:
            pass
        return state

    async def _reset_daily_if_needed(self, state: dict) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        if state.get("last_reset_date") != today:
            state["auto_trades_today"] = 0
            state["last_reset_date"] = today
        return state

    async def log_audit(
        self,
        event_type: str,
        detail: str,
        *,
        ticker: str = "",
        strategy_id: str = "",
        strategy_name: str = "",
        verdict: str = "",
        meta: dict | None = None,
    ) -> dict | None:
        entry = {
            "event_type": event_type,
            "detail": detail,
            "ticker": ticker,
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "verdict": verdict,
            "meta": meta or {},
        }
        try:
            storage = await get_storage()
            return await storage.create_automation_audit(entry)
        except RuntimeError:
            logger.info("automation_audit", **entry)
            return entry

    async def enable(self) -> dict:
        state = await self._get_state()
        state["enabled"] = True
        state["enabled_at"] = datetime.now(timezone.utc).isoformat()
        state["disabled_reason"] = ""
        state = await self._reset_daily_if_needed(state)
        await self._save_state(state)
        await self.log_audit("automation_enabled", "Constrained automation enabled by user")
        logger.info("automation_enabled")
        return state

    async def disable(self, reason: str = "Disabled by user") -> dict:
        state = await self._get_state()
        state["enabled"] = False
        state["disabled_at"] = datetime.now(timezone.utc).isoformat()
        state["disabled_reason"] = reason
        await self._save_state(state)
        await self.log_audit("automation_disabled", reason)
        await self.monitoring.emit_alert(
            event_type="automation_disabled",
            severity="high",
            title="Automation Disabled",
            detail=reason,
            dedupe=False,
        )
        logger.warning("automation_disabled", reason=reason)
        return state

    async def record_auto_trade(self, ticker: str, strategy_name: str, detail: str) -> None:
        state = await self._get_state()
        state = await self._reset_daily_if_needed(state)
        state["auto_trades_today"] = int(state.get("auto_trades_today", 0)) + 1
        await self._save_state(state)
        await self.log_audit(
            "auto_executed",
            detail,
            ticker=ticker,
            strategy_name=strategy_name,
            verdict="ALLOW",
        )

    async def can_auto_execute(
        self,
        *,
        strategy_auto_approve: bool,
        verdict: str,
    ) -> tuple[bool, str]:
        if not strategy_auto_approve:
            return False, "Strategy auto-approve is off"
        if verdict != "ALLOW":
            return False, f"Verdict is {verdict} — only ALLOW auto-executes"
        if not settings.automation_feature_enabled:
            return False, "Automation feature disabled in config"
        if not settings.strategies_auto_execute:
            return False, "STRATEGIES_AUTO_EXECUTE is false"

        state = await self._get_state()
        state = await self._reset_daily_if_needed(state)
        await self._save_state(state)

        if not state.get("enabled"):
            return False, "Automation master switch is off"

        halted, halt_reason = await self.monitoring.is_trading_halted()
        if halted:
            return False, f"Trading halted: {halt_reason}"

        automation_ok, gate_reason = await self.validation.automation_allowed()
        if not automation_ok:
            return False, gate_reason or "Validation gate not passed"

        if int(state.get("auto_trades_today", 0)) >= settings.automation_max_daily_trades:
            return False, (
                f"Daily auto-trade cap reached "
                f"({settings.automation_max_daily_trades})"
            )

        return True, ""

    async def get_status(self) -> dict:
        state = await self._get_state()
        state = await self._reset_daily_if_needed(state)
        await self._save_state(state)

        halted, halt_reason = await self.monitoring.is_trading_halted()
        validation_ok, validation_report = await self.validation.check_gate()

        can_run, block_reason = await self.can_auto_execute(
            strategy_auto_approve=True,
            verdict="ALLOW",
        )
        # can_auto_execute requires master switch; compute readiness separately
        ready = (
            settings.automation_feature_enabled
            and settings.strategies_auto_execute
            and state.get("enabled")
            and not halted
            and validation_ok
            and int(state.get("auto_trades_today", 0)) < settings.automation_max_daily_trades
        )

        try:
            storage = await get_storage()
            audit = await storage.list_automation_audit(limit=20)
        except RuntimeError:
            audit = []

        return {
            "master_enabled": bool(state.get("enabled")),
            "ready": ready,
            "block_reason": block_reason if not can_run and state.get("enabled") else (
                halt_reason if halted else (
                    validation_report.get("summary") if not validation_ok else ""
                )
            ),
            "trading_halted": halted,
            "validation_unlocked": validation_ok,
            "auto_trades_today": int(state.get("auto_trades_today", 0)),
            "auto_trades_remaining": max(
                0,
                settings.automation_max_daily_trades - int(state.get("auto_trades_today", 0)),
            ),
            "state": state,
            "bounds": {
                "max_daily_auto_trades": settings.automation_max_daily_trades,
                "max_trade_usd": settings.risk_max_trade_usd,
                "allowed_verdicts": ["ALLOW"],
                "options_allowed": settings.risk_allow_options,
                "require_manual_approval_default": settings.risk_require_manual_approval,
            },
            "validation_summary": validation_report.get("summary"),
            "recent_audit": audit,
        }

    async def list_audit(self, limit: int = 50) -> list[dict]:
        try:
            storage = await get_storage()
            return await storage.list_automation_audit(limit=limit)
        except RuntimeError:
            return []
