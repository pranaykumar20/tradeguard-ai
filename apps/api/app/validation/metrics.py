"""Performance metrics — pure functions over trade history."""

from __future__ import annotations

import statistics
from datetime import datetime
from math import sqrt


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_metrics(
    trades: list[dict],
    *,
    starting_capital: float = 10_000.0,
    rule_violation_count: int = 0,
) -> dict:
    filled = [
        t
        for t in trades
        if t.get("status") == "filled" and t.get("pnl") is not None
    ]
    filled_sorted = sorted(
        filled,
        key=lambda t: _parse_dt(t.get("created_at")) or datetime.min,
    )
    returns = [float(t["pnl"]) for t in filled_sorted]

    wins = [r for r in returns if r > 0]
    win_rate = round(len(wins) / len(returns) * 100, 1) if returns else 0.0
    total_pnl = round(sum(returns), 2)

    if len(returns) >= 2:
        mean_r = statistics.mean(returns)
        stdev = statistics.stdev(returns)
        sharpe = round((mean_r / stdev) * sqrt(252), 2) if stdev > 0 else 0.0
    elif len(returns) == 1:
        sharpe = 1.0 if returns[0] > 0 else -1.0
    else:
        sharpe = 0.0

    equity = starting_capital
    peak = starting_capital
    max_dd_pct = 0.0
    for r in returns:
        equity += r
        peak = max(peak, equity)
        if peak > 0:
            dd_pct = (peak - equity) / peak * 100
            max_dd_pct = max(max_dd_pct, dd_pct)
    max_dd_pct = round(max_dd_pct, 2)

    dates = [_parse_dt(t.get("created_at")) for t in filled_sorted]
    dates = [d for d in dates if d is not None]
    if len(dates) >= 2:
        span_days = (max(dates) - min(dates)).days
        track_record_months = round(span_days / 30.44, 1)
    elif len(dates) == 1:
        track_record_months = 0.0
    else:
        track_record_months = 0.0

    blocked = len([t for t in trades if t.get("verdict") == "BLOCK" or t.get("status") == "rejected"])

    return {
        "track_record_months": track_record_months,
        "total_trades": len(trades),
        "filled_trades": len(filled),
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd_pct,
        "rule_violation_count": rule_violation_count + blocked,
        "starting_capital": starting_capital,
    }


def evaluate_gate(metrics: dict, thresholds: dict) -> tuple[bool, list[dict], str]:
    checks = [
        {
            "name": "track_record_months",
            "label": "Track record",
            "passed": metrics["track_record_months"] >= thresholds["min_months"],
            "actual": metrics["track_record_months"],
            "required": f">= {thresholds['min_months']} months",
        },
        {
            "name": "total_pnl",
            "label": "Total P&L",
            "passed": metrics["total_pnl"] > thresholds["min_total_pnl"],
            "actual": metrics["total_pnl"],
            "required": f"> ${thresholds['min_total_pnl']}",
        },
        {
            "name": "sharpe_ratio",
            "label": "Sharpe ratio",
            "passed": metrics["sharpe_ratio"] >= thresholds["min_sharpe"],
            "actual": metrics["sharpe_ratio"],
            "required": f">= {thresholds['min_sharpe']}",
        },
        {
            "name": "max_drawdown_pct",
            "label": "Max drawdown",
            "passed": metrics["max_drawdown_pct"] <= thresholds["max_drawdown_pct"],
            "actual": metrics["max_drawdown_pct"],
            "required": f"<= {thresholds['max_drawdown_pct']}%",
        },
        {
            "name": "win_rate",
            "label": "Win rate",
            "passed": metrics["win_rate"] >= thresholds["min_win_rate"],
            "actual": metrics["win_rate"],
            "required": f">= {thresholds['min_win_rate']}%",
        },
        {
            "name": "filled_trades",
            "label": "Filled trades",
            "passed": metrics["filled_trades"] >= thresholds["min_filled_trades"],
            "actual": metrics["filled_trades"],
            "required": f">= {thresholds['min_filled_trades']}",
        },
        {
            "name": "rule_violations",
            "label": "Rule violations",
            "passed": metrics["rule_violation_count"] <= thresholds["max_rule_violations"],
            "actual": metrics["rule_violation_count"],
            "required": f"<= {thresholds['max_rule_violations']}",
        },
    ]

    passed = all(c["passed"] for c in checks)
    failed = [c["label"] for c in checks if not c["passed"]]
    if passed:
        summary = "Validation gate passed — Phase 4.4 automation unlocked."
    elif failed:
        summary = f"Validation gate blocked: {', '.join(failed)}."
    else:
        summary = "Validation gate blocked."

    return passed, checks, summary
