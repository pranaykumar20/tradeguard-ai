"""Real-time PnL monitoring, circuit breaker, and alert dispatch."""

from datetime import datetime, timezone

import structlog

from app.core.config import settings
from app.core.user_context import get_current_user_id
from app.db.storage import get_storage
from app.mcp.factory import get_mcp_client
from app.portfolio.demo import demo_portfolio
from app.providers.alerts.factory import get_alert_provider
from app.risk.engine import RiskEngine

logger = structlog.get_logger()

DEFAULT_TRADING_STATE = {
    "halted": False,
    "reason": "",
    "halted_at": None,
    "daily_pnl_at_halt": None,
    "resumed_at": None,
    "last_check_at": None,
}

DEDUPE_MINUTES = 15


class MonitoringService:
    def __init__(self):
        self.risk = RiskEngine()
        self.mcp = get_mcp_client()
        self.alerts = get_alert_provider()

    async def get_trading_state(self) -> dict:
        try:
            storage = await get_storage()
        except RuntimeError:
            return dict(DEFAULT_TRADING_STATE)
        state = await storage.get_app_state("trading")
        return {**DEFAULT_TRADING_STATE, **(state or {})}

    async def is_trading_halted(self) -> tuple[bool, str]:
        state = await self.get_trading_state()
        if state.get("halted"):
            return True, state.get("reason") or "Trading halted by monitoring"
        return False, ""

    async def halt_trading(self, reason: str, daily_pnl: float | None = None) -> dict:
        try:
            storage = await get_storage()
        except RuntimeError:
            return dict(DEFAULT_TRADING_STATE)
        state = {
            "halted": True,
            "reason": reason,
            "halted_at": datetime.now(timezone.utc).isoformat(),
            "daily_pnl_at_halt": daily_pnl,
            "resumed_at": None,
            "last_check_at": datetime.now(timezone.utc).isoformat(),
        }
        await storage.set_app_state("trading", state)
        logger.warning("trading_halted", reason=reason, daily_pnl=daily_pnl)
        return state

    async def resume_trading(self) -> dict:
        try:
            storage = await get_storage()
        except RuntimeError:
            return dict(DEFAULT_TRADING_STATE)
        state = {
            "halted": False,
            "reason": "",
            "halted_at": None,
            "daily_pnl_at_halt": None,
            "resumed_at": datetime.now(timezone.utc).isoformat(),
            "last_check_at": datetime.now(timezone.utc).isoformat(),
        }
        await storage.set_app_state("trading", state)
        logger.info("trading_resumed")
        await self.emit_alert(
            event_type="trading_resumed",
            severity="medium",
            title="Trading Resumed",
            detail="Manual resume — new trades allowed if risk rules pass.",
        )
        return state

    async def _portfolio_snapshot(self) -> dict:
        if settings.robinhood_mcp_enabled:
            try:
                snap = await self.mcp.get_portfolio_snapshot()
                if snap.get("positions"):
                    return snap
            except Exception as exc:
                await self.emit_alert(
                    event_type="mcp_failure",
                    severity="high",
                    title="MCP Portfolio Unavailable",
                    detail=f"Failed to fetch live portfolio: {exc}",
                )
        return demo_portfolio()

    async def _recent_alert_exists(self, event_type: str, minutes: int = DEDUPE_MINUTES) -> bool:
        try:
            storage = await get_storage()
        except RuntimeError:
            return False
        events = await storage.list_alert_events(limit=20)
        cutoff = datetime.now(timezone.utc).timestamp() - minutes * 60
        for event in events:
            if event.get("event_type") != event_type:
                continue
            created = event.get("created_at")
            if not created:
                continue
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                if ts >= cutoff:
                    return True
            except ValueError:
                continue
        return False

    async def emit_alert(
        self,
        event_type: str,
        severity: str,
        title: str,
        detail: str,
        *,
        dedupe: bool = True,
    ) -> dict | None:
        if dedupe and await self._recent_alert_exists(event_type):
            return None

        result = await self.alerts.send(title, detail, severity, event_type)
        channels = result.get("channels") or [result.get("provider", "unknown")]
        try:
            storage = await get_storage()
        except RuntimeError:
            return {
                "id": "ephemeral",
                "event_type": event_type,
                "severity": severity,
                "title": title,
                "detail": detail,
                "channels_sent": channels,
            }
        event = await storage.create_alert_event(
            {
                "event_type": event_type,
                "severity": severity,
                "title": title,
                "detail": detail,
                "channels_sent": channels,
            }
        )
        if settings.push_notifications_enabled:
            from app.services.push import PushNotificationService

            await PushNotificationService().notify(title, detail, event_type, severity)
        return event

    async def notify_block(self, ticker: str, blocks: list[str]) -> None:
        if not blocks:
            return
        await self.emit_alert(
            event_type="block_event",
            severity="high",
            title=f"Trade Blocked — {ticker}",
            detail="; ".join(blocks),
        )

    async def run_check(self) -> dict:
        if not settings.monitoring_enabled:
            return {"status": "disabled"}

        portfolio = await self._portfolio_snapshot()
        daily_pnl = float(portfolio.get("daily_pnl", 0))
        max_drawdown = float(portfolio.get("max_drawdown_est", 0))
        snapshot = await self.risk.portfolio_snapshot()

        checks: list[dict] = []
        halted, halt_reason = await self.is_trading_halted()

        if settings.trading_halt_on_daily_loss:
            if daily_pnl <= -settings.risk_max_daily_loss_usd:
                reason = (
                    f"Daily loss ${abs(daily_pnl):.2f} exceeded "
                    f"${settings.risk_max_daily_loss_usd:.2f} limit"
                )
                if not halted:
                    await self.halt_trading(reason, daily_pnl=daily_pnl)
                    await self.emit_alert(
                        event_type="daily_loss_halt",
                        severity="critical",
                        title="Trading Halted — Daily Loss Limit",
                        detail=reason,
                        dedupe=False,
                    )
                checks.append({"name": "daily_loss", "status": "fail", "detail": reason})
                halted, halt_reason = True, reason
            else:
                checks.append(
                    {
                        "name": "daily_loss",
                        "status": "ok",
                        "detail": f"Daily P&L ${daily_pnl:.2f}",
                    }
                )

        if max_drawdown >= settings.max_drawdown_alert_pct:
            detail = f"Estimated max drawdown {max_drawdown:.1f}% exceeds {settings.max_drawdown_alert_pct:.0f}% threshold"
            await self.emit_alert(
                event_type="drawdown_warning",
                severity="high",
                title="Drawdown Warning",
                detail=detail,
            )
            checks.append({"name": "drawdown", "status": "warn", "detail": detail})
        else:
            checks.append(
                {
                    "name": "drawdown",
                    "status": "ok",
                    "detail": f"Max drawdown est. {max_drawdown:.1f}%",
                }
            )

        if settings.robinhood_mcp_enabled:
            try:
                await self.mcp.get_quote("SPY")
                checks.append({"name": "mcp", "status": "ok", "detail": "MCP reachable"})
            except Exception as exc:
                detail = f"MCP health check failed: {exc}"
                await self.emit_alert(
                    event_type="mcp_failure",
                    severity="high",
                    title="MCP Health Check Failed",
                    detail=detail,
                )
                checks.append({"name": "mcp", "status": "fail", "detail": detail})
        else:
            checks.append({"name": "mcp", "status": "skipped", "detail": "MCP disabled (mock mode)"})

        try:
            storage = await get_storage()
            await storage.set_app_state(
                "trading",
                {
                    **await self.get_trading_state(),
                    "last_check_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except RuntimeError:
            pass

        return {
            "status": "halted" if halted else "ok",
            "user_id": get_current_user_id(),
            "trading_halted": halted,
            "halt_reason": halt_reason if halted else None,
            "daily_pnl": daily_pnl,
            "max_drawdown_est": max_drawdown,
            "portfolio_value": portfolio.get("account_value"),
            "checks": checks,
            "alerts": snapshot.get("alerts", []),
            "alert_provider": settings.active_alert_provider,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_status(self) -> dict:
        state = await self.get_trading_state()
        portfolio = await self._portfolio_snapshot()
        halted, reason = await self.is_trading_halted()
        try:
            storage = await get_storage()
            recent = await storage.list_alert_events(limit=10)
        except RuntimeError:
            recent = []
        return {
            "monitoring_enabled": settings.monitoring_enabled,
            "user_id": get_current_user_id(),
            "trading_halted": halted,
            "halt_reason": reason if halted else None,
            "trading_state": state,
            "daily_pnl": portfolio.get("daily_pnl"),
            "portfolio_value": portfolio.get("account_value"),
            "max_drawdown_est": portfolio.get("max_drawdown_est"),
            "daily_loss_limit": settings.risk_max_daily_loss_usd,
            "drawdown_alert_pct": settings.max_drawdown_alert_pct,
            "alert_provider": settings.active_alert_provider,
            "recent_alerts": recent,
        }
