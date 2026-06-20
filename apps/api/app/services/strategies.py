"""Semi-automated trade strategies — evaluate, propose, auto-approve ALLOW-only."""

from datetime import datetime, timezone

import structlog

from app.core.config import settings
from app.db.storage import get_storage
from app.services.automation import AutomationService
from app.services.execution import ExecutionService
from app.services.monitoring import MonitoringService
from app.services.validation import ValidationService
from app.strategies.evaluator import evaluate_trigger, strategy_summary

logger = structlog.get_logger()

DEFAULT_STRATEGIES = [
    {
        "name": "Tech overweight trim",
        "description": "Sell 1 QQQ when Technology sector exposure exceeds 25%",
        "strategy_type": "sector_exposure",
        "config": {
            "sector": "Technology",
            "threshold_pct": 25.0,
            "comparison": "above",
            "action_ticker": "QQQ",
            "action_side": "sell",
            "quantity": 1,
        },
        "auto_approve": True,
        "enabled": False,
    },
]


class StrategyService:
    def __init__(self):
        self.execution = ExecutionService()
        self.monitoring = MonitoringService()
        self.validation = ValidationService()
        self.automation = AutomationService()

    async def ensure_defaults(self) -> None:
        try:
            storage = await get_storage()
        except RuntimeError:
            return
        existing = await storage.list_trade_strategies()
        if existing:
            return
        for template in DEFAULT_STRATEGIES:
            await storage.create_trade_strategy(template)
        logger.info("default_strategies_seeded", count=len(DEFAULT_STRATEGIES))

    async def list_strategies(self) -> list[dict]:
        storage = await get_storage()
        strategies = await storage.list_trade_strategies()
        return [{**s, "summary": strategy_summary(s)} for s in strategies]

    async def get_strategy(self, strategy_id: str) -> dict | None:
        storage = await get_storage()
        strategy = await storage.get_trade_strategy(strategy_id)
        if not strategy:
            return None
        return {**strategy, "summary": strategy_summary(strategy)}

    async def create_strategy(self, data: dict) -> dict:
        storage = await get_storage()
        strategy = await storage.create_trade_strategy(data)
        return {**strategy, "summary": strategy_summary(strategy)}

    async def update_strategy(self, strategy_id: str, updates: dict) -> dict | None:
        storage = await get_storage()
        strategy = await storage.update_trade_strategy(strategy_id, updates)
        if not strategy:
            return None
        return {**strategy, "summary": strategy_summary(strategy)}

    async def delete_strategy(self, strategy_id: str) -> bool:
        storage = await get_storage()
        return await storage.delete_trade_strategy(strategy_id)

    async def list_proposals(self, strategy_id: str | None = None, limit: int = 50) -> list[dict]:
        storage = await get_storage()
        return await storage.list_strategy_proposals(strategy_id=strategy_id, limit=limit)

    async def _save_proposal(self, strategy: dict, intent: dict | None, preview: dict | None, status: str, **extra) -> dict:
        storage = await get_storage()
        order = (preview or {}).get("order") or {}
        risk = (preview or {}).get("risk") or {}
        return await storage.create_strategy_proposal(
            {
                "strategy_id": strategy["id"],
                "strategy_name": strategy["name"],
                "ticker": order.get("ticker") or (intent or {}).get("ticker", ""),
                "side": order.get("side") or (intent or {}).get("side", ""),
                "quantity": order.get("quantity") or (intent or {}).get("quantity", 0),
                "limit_price": order.get("limit_price"),
                "trigger_context": (intent or {}).get("trigger_context"),
                "trigger_reason": (intent or {}).get("trigger_reason", ""),
                "risk_preview": risk,
                "status": status,
                "approval_id": extra.get("approval_id"),
                "execution_result": extra.get("execution_result"),
                "notes": extra.get("notes", ""),
            }
        )

    async def evaluate_strategy(self, strategy_id: str) -> dict:
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")
        if not strategy.get("enabled"):
            return {"status": "disabled", "strategy": strategy}

        portfolio = await self.execution._portfolio_for_risk()
        intent = evaluate_trigger(
            strategy["strategy_type"],
            strategy.get("config") or {},
            portfolio,
        )
        if not intent:
            proposal = await self._save_proposal(strategy, None, None, "not_triggered")
            return {
                "status": "not_triggered",
                "strategy": strategy,
                "proposal": proposal,
            }

        preview = await self.execution.preview_order(
            ticker=intent["ticker"],
            side=intent["side"],
            quantity=intent["quantity"],
        )
        risk = preview["risk"]
        halted, halt_reason = await self.monitoring.is_trading_halted()

        result: dict = {
            "status": "proposed",
            "strategy": strategy,
            "intent": intent,
            "preview": preview,
        }

        if not risk.get("allowed"):
            proposal = await self._save_proposal(
                strategy,
                intent,
                preview,
                "blocked",
                notes="; ".join(risk.get("blocks", [])),
            )
            await self.monitoring.notify_block(intent["ticker"], risk.get("blocks", []))
            result.update({"status": "blocked", "proposal": proposal})
            return result

        gate_reason = ""
        can_auto, gate_reason = await self.automation.can_auto_execute(
            strategy_auto_approve=bool(strategy.get("auto_approve")),
            verdict=risk.get("verdict", "BLOCK"),
        )
        if strategy.get("auto_approve") and risk.get("verdict") == "ALLOW" and not can_auto and gate_reason:
            await self.automation.log_audit(
                "auto_blocked",
                gate_reason,
                ticker=intent["ticker"],
                strategy_id=strategy["id"],
                strategy_name=strategy["name"],
                verdict=risk.get("verdict", ""),
            )

        if can_auto:
            submitted = await self.execution.submit_for_approval(
                ticker=intent["ticker"],
                side=intent["side"],
                quantity=intent["quantity"],
                limit_price=preview["order"]["limit_price"],
                notes=f"Auto-approved strategy: {strategy['name']} — {intent['trigger_reason']}",
            )
            if submitted["status"] != "pending":
                proposal = await self._save_proposal(
                    strategy,
                    intent,
                    preview,
                    "blocked",
                    notes=submitted.get("reason", "Submit blocked"),
                )
                result.update({"status": "blocked", "proposal": proposal})
                return result

            approval_id = submitted["approval"]["id"]
            executed = await self.execution.approve(approval_id)
            await self.automation.record_auto_trade(
                ticker=intent["ticker"],
                strategy_name=strategy["name"],
                detail=f"{intent['side']} {intent['quantity']} {intent['ticker']} — {intent['trigger_reason']}",
            )
            proposal = await self._save_proposal(
                strategy,
                intent,
                preview,
                "auto_executed",
                approval_id=approval_id,
                execution_result=executed.get("execution"),
                notes=f"Auto-executed (ALLOW) — {intent['trigger_reason']}",
            )
            await self.monitoring.emit_alert(
                event_type="strategy_auto_executed",
                severity="medium",
                title=f"Strategy auto-executed: {strategy['name']}",
                detail=f"{intent['side']} {intent['quantity']} {intent['ticker']} — {intent['trigger_reason']}",
            )
            result.update({"status": "auto_executed", "proposal": proposal, "execution": executed})
            return result

        if halted:
            proposal = await self._save_proposal(
                strategy,
                intent,
                preview,
                "blocked",
                notes=f"Trading halted: {halt_reason}",
            )
            result.update({"status": "blocked", "proposal": proposal})
            return result

        submit_notes = f"Strategy proposal: {strategy['name']} — {intent['trigger_reason']}"
        if gate_reason:
            submit_notes = f"Validation gate blocked auto-execute: {gate_reason}"

        submitted = await self.execution.submit_for_approval(
            ticker=intent["ticker"],
            side=intent["side"],
            quantity=intent["quantity"],
            limit_price=preview["order"]["limit_price"],
            notes=submit_notes,
        )
        if submitted["status"] == "pending":
            proposal = await self._save_proposal(
                strategy,
                intent,
                preview,
                "pending_approval",
                approval_id=submitted["approval"]["id"],
                notes=gate_reason or intent["trigger_reason"],
            )
            result.update({
                "status": "pending_approval",
                "proposal": proposal,
                "approval": submitted["approval"],
                "gate_blocked": bool(gate_reason),
            })
        else:
            proposal = await self._save_proposal(
                strategy,
                intent,
                preview,
                "blocked",
                notes=submitted.get("reason", ""),
            )
            result.update({"status": "blocked", "proposal": proposal})
        return result

    async def run_all_enabled(self) -> dict:
        if not settings.strategies_enabled:
            return {"status": "disabled", "results": []}

        strategies = await self.list_strategies()
        results = []
        for strategy in strategies:
            if not strategy.get("enabled"):
                continue
            try:
                result = await self.evaluate_strategy(strategy["id"])
                results.append(result)
            except Exception as exc:
                logger.error("strategy_eval_failed", strategy_id=strategy["id"], error=str(exc))
                results.append({"status": "error", "strategy_id": strategy["id"], "error": str(exc)})
        return {
            "status": "ok",
            "evaluated": len(results),
            "results": results,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def templates(self) -> list[dict]:
        return [{**t, "summary": strategy_summary(t)} for t in DEFAULT_STRATEGIES]
