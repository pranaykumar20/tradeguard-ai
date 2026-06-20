"""Agentic onboarding wizard — track setup progress per user."""

from datetime import datetime, timezone

from app.core.config import settings
from app.db.storage import get_storage

ONBOARDING_STEPS = [
    {
        "id": "welcome",
        "title": "Welcome to TradeGuard",
        "description": "AI risk manager with guarded Robinhood MCP execution.",
        "auto": True,
    },
    {
        "id": "connect_mcp",
        "title": "Connect Robinhood MCP",
        "description": "Enable Agentic Trading and set ROBINHOOD_MCP_URL in your API env.",
        "auto": True,
    },
    {
        "id": "fund_account",
        "title": "Fund Agentic account",
        "description": "Start with $500–$1,000 in a separate Agentic account.",
        "auto": False,
    },
    {
        "id": "set_limits",
        "title": "Review risk limits",
        "description": "Confirm max trade size, daily loss, and manual approval settings.",
        "auto": True,
    },
    {
        "id": "enable_monitoring",
        "title": "Enable monitoring",
        "description": "Turn on PnL monitoring and alert channels.",
        "auto": True,
    },
    {
        "id": "complete",
        "title": "Ready to trade",
        "description": "Submit trades through the approval queue.",
        "auto": False,
    },
]


class OnboardingService:
    async def _completed_manual(self) -> set[str]:
        storage = await get_storage()
        state = await storage.get_app_state("onboarding") or {}
        return set(state.get("completed_manual", []))

    async def _save_manual(self, completed: set[str]) -> None:
        storage = await get_storage()
        state = await storage.get_app_state("onboarding") or {}
        state["completed_manual"] = sorted(completed)
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await storage.set_app_state("onboarding", state)

    def _auto_complete(self, step_id: str) -> bool:
        if step_id == "welcome":
            return True
        if step_id == "connect_mcp":
            return settings.robinhood_mcp_enabled and bool(settings.robinhood_mcp_url)
        if step_id == "set_limits":
            return settings.risk_require_manual_approval and settings.risk_max_trade_usd <= 500
        if step_id == "enable_monitoring":
            return settings.monitoring_enabled
        return False

    async def get_status(self) -> dict:
        manual = await self._completed_manual()
        steps = []
        completed_count = 0
        for step in ONBOARDING_STEPS:
            sid = step["id"]
            done = self._auto_complete(sid) or sid in manual
            if done:
                completed_count += 1
            steps.append({**step, "completed": done, "manual_confirm": not step["auto"]})

        total = len(ONBOARDING_STEPS)
        return {
            "steps": steps,
            "completed_count": completed_count,
            "total_steps": total,
            "progress_pct": round(completed_count / total * 100) if total else 0,
            "complete": completed_count >= total,
            "risk_limits": {
                "max_trade_usd": settings.risk_max_trade_usd,
                "max_daily_loss_usd": settings.risk_max_daily_loss_usd,
                "require_manual_approval": settings.risk_require_manual_approval,
                "allow_options": settings.risk_allow_options,
            },
            "mcp": {
                "enabled": settings.robinhood_mcp_enabled,
                "configured": bool(settings.robinhood_mcp_url),
            },
            "monitoring_enabled": settings.monitoring_enabled,
        }

    async def complete_step(self, step_id: str) -> dict:
        valid = {s["id"] for s in ONBOARDING_STEPS}
        if step_id not in valid:
            raise ValueError(f"Unknown onboarding step: {step_id}")
        manual = await self._completed_manual()
        manual.add(step_id)
        await self._save_manual(manual)
        return await self.get_status()

    async def reset(self) -> dict:
        storage = await get_storage()
        await storage.set_app_state("onboarding", {"completed_manual": [], "updated_at": None})
        return await self.get_status()
