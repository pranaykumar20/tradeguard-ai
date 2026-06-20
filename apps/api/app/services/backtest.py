"""Journal backtesting — replay strategy rules against historical trades."""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.storage import get_storage
from app.portfolio.demo import demo_portfolio
from app.strategies.evaluator import evaluate_trigger
from app.validation.metrics import compute_metrics


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class BacktestService:
    async def run(self, strategy_id: str, days: int = 90) -> dict:
        storage = await get_storage()
        strategy = await storage.get_trade_strategy(strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        trades = [
            t
            for t in await storage.list_paper_trades(limit=1000)
            if _parse_dt(t.get("created_at")) and _parse_dt(t.get("created_at")) >= cutoff
        ]
        trades.sort(key=lambda t: _parse_dt(t.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc))

        proposals = [
            p
            for p in await storage.list_strategy_proposals(strategy_id=strategy_id, limit=200)
            if _parse_dt(p.get("created_at")) and _parse_dt(p.get("created_at")) >= cutoff
        ]

        config = strategy.get("config") or {}
        action_ticker = (config.get("action_ticker") or "").upper()
        matched_trades = [t for t in trades if t.get("ticker") == action_ticker]

        portfolio = demo_portfolio()
        signals: list[dict] = []
        for trade in trades:
            intent = evaluate_trigger(strategy.get("strategy_type", ""), config, portfolio)
            if intent:
                signals.append(
                    {
                        "at": trade.get("created_at"),
                        "trigger_reason": intent.get("trigger_reason"),
                        "would_trade": intent,
                        "nearby_journal_trade": trade.get("ticker"),
                    }
                )
            self._apply_trade_to_portfolio(portfolio, trade)

        all_metrics = compute_metrics(
            trades, starting_capital=settings.validation_starting_capital
        )
        matched_metrics = compute_metrics(
            matched_trades, starting_capital=settings.validation_starting_capital
        )

        proposal_outcomes: dict[str, int] = {}
        for p in proposals:
            status = p.get("status", "unknown")
            proposal_outcomes[status] = proposal_outcomes.get(status, 0) + 1

        return {
            "strategy": {
                "id": strategy["id"],
                "name": strategy["name"],
                "strategy_type": strategy.get("strategy_type"),
                "config": config,
            },
            "period_days": days,
            "journal_trades_in_period": len(trades),
            "matched_action_trades": len(matched_trades),
            "simulated_signals": len(signals),
            "proposal_count": len(proposals),
            "proposal_outcomes": proposal_outcomes,
            "metrics_all_trades": all_metrics,
            "metrics_matched_trades": matched_metrics,
            "signals": signals[:25],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _apply_trade_to_portfolio(portfolio: dict, trade: dict) -> None:
        ticker = trade.get("ticker", "").upper()
        positions = portfolio.setdefault("positions", {})
        qty = float(trade.get("quantity", 0))
        pos = positions.setdefault(ticker, {"shares": 0, "weight_pct": 0, "sector": "Technology"})
        if trade.get("side") == "buy":
            pos["shares"] = float(pos.get("shares", 0)) + qty
        else:
            pos["shares"] = max(0, float(pos.get("shares", 0)) - qty)
