"""Performance validation gate — blocks Phase 4.4 automation until journal metrics pass."""

from datetime import datetime, timedelta, timezone

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.validation.metrics import compute_metrics, evaluate_gate

logger = structlog.get_logger()

TICKERS = ["NVDA", "MSFT", "META", "QQQ", "TSLA", "GBTC"]


class ValidationService:
    def thresholds(self) -> dict:
        return {
            "min_months": settings.validation_min_months,
            "min_sharpe": settings.validation_min_sharpe,
            "max_drawdown_pct": settings.validation_max_drawdown_pct,
            "min_win_rate": settings.validation_min_win_rate,
            "min_total_pnl": settings.validation_min_total_pnl,
            "max_rule_violations": settings.validation_max_rule_violations,
            "min_filled_trades": settings.validation_min_filled_trades,
        }

    async def build_report(self) -> dict:
        try:
            storage = await get_storage()
            trades = await storage.list_paper_trades(limit=500)
        except RuntimeError:
            trades = []

        metrics = compute_metrics(
            trades,
            starting_capital=settings.validation_starting_capital,
        )
        thresholds = self.thresholds()
        passed, checks, summary = evaluate_gate(metrics, thresholds)

        dev_bypass = settings.validation_dev_bypass and settings.app_env == "development"
        automation_unlocked = passed or dev_bypass

        report = {
            "passed": passed,
            "automation_unlocked": automation_unlocked,
            "dev_bypass_active": dev_bypass,
            "gate_enabled": settings.validation_gate_enabled,
            "summary": summary if not dev_bypass else "Dev bypass active — automation unlocked for testing.",
            "metrics": metrics,
            "thresholds": thresholds,
            "checks": checks,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            storage = await get_storage()
            await storage.set_app_state("validation_report", report)
        except RuntimeError:
            pass

        return report

    async def check_gate(self) -> tuple[bool, dict]:
        report = await self.build_report()
        if not settings.validation_gate_enabled:
            report["automation_unlocked"] = True
            report["summary"] = "Validation gate disabled."
            return True, report
        return report["automation_unlocked"], report

    async def automation_allowed(self) -> tuple[bool, str]:
        allowed, report = await self.check_gate()
        if allowed:
            return True, ""
        return False, report.get("summary", "Validation gate not passed")

    async def seed_demo_track_record(self) -> dict:
        if not settings.validation_allow_demo_seed:
            raise ValueError("Demo seed disabled — set VALIDATION_ALLOW_DEMO_SEED=true")

        storage = await get_storage()
        now = datetime.now(timezone.utc)
        created = 0

        for i in range(48):
            days_ago = 95 - int(i * 2)
            ts = now - timedelta(days=days_ago)
            ticker = TICKERS[i % len(TICKERS)]
            side = "buy" if i % 3 != 0 else "sell"
            pnl = round(8.0 + (i % 5) * 3.5 - (i % 7) * 2.0, 2)
            if i % 11 == 0:
                pnl = round(-abs(pnl) * 0.4, 2)

            await storage.create_paper_trade(
                {
                    "ticker": ticker,
                    "side": side,
                    "quantity": 1,
                    "limit_price": 100 + (i % 20),
                    "fill_price": 100 + (i % 20),
                    "status": "filled",
                    "verdict": "ALLOW",
                    "reason": "Demo validation seed",
                    "pnl": pnl,
                    "created_at": ts.isoformat(),
                }
            )
            created += 1

        for j in range(2):
            await storage.create_paper_trade(
                {
                    "ticker": "NVDA",
                    "side": "buy",
                    "quantity": 10,
                    "limit_price": 500,
                    "fill_price": None,
                    "status": "rejected",
                    "verdict": "BLOCK",
                    "reason": "Demo blocked trade",
                    "pnl": None,
                    "created_at": (now - timedelta(days=30 + j)).isoformat(),
                }
            )

        report = await self.build_report()
        logger.info("validation_demo_seeded", trades=created, passed=report["passed"])
        return {"seeded_trades": created, "report": report}
