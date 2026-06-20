"""Strategy trigger evaluation — pure logic, no I/O."""

from typing import Any


def evaluate_trigger(strategy_type: str, config: dict, portfolio: dict) -> dict | None:
    if strategy_type == "sector_exposure":
        return _sector_exposure(config, portfolio)
    return None


def _sector_exposure(config: dict, portfolio: dict) -> dict | None:
    sector = config.get("sector", "Technology")
    threshold = float(config.get("threshold_pct", 25.0))
    comparison = config.get("comparison", "above")
    current = float(portfolio.get("sector_exposure", {}).get(sector, 0))

    if comparison == "above" and current <= threshold:
        return None
    if comparison == "below" and current >= threshold:
        return None

    return {
        "ticker": config["action_ticker"].upper(),
        "side": config["action_side"],
        "quantity": float(config.get("quantity", 1)),
        "trigger_reason": (
            f"{sector} exposure {current:.1f}% is {comparison} {threshold:.1f}% threshold"
        ),
        "trigger_context": {
            "sector": sector,
            "current_pct": current,
            "threshold_pct": threshold,
            "comparison": comparison,
        },
    }


def strategy_summary(strategy: dict) -> str:
    cfg = strategy.get("config") or {}
    stype = strategy.get("strategy_type", "")
    if stype == "sector_exposure":
        return (
            f"When {cfg.get('sector')} is {cfg.get('comparison', 'above')} "
            f"{cfg.get('threshold_pct')}%, "
            f"{cfg.get('action_side')} {cfg.get('quantity')} {cfg.get('action_ticker')}"
        )
    return stype
