"""Advanced portfolio risk metrics — VaR, correlation, stress tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.portfolio.demo import demo_portfolio
from app.providers.market.factory import get_market_data_provider

ALLOWED = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"]


async def _returns_matrix(tickers: list[str], days: int = 90) -> pd.DataFrame:
    provider = get_market_data_provider()
    series = {}
    for ticker in tickers:
        bars = await provider.get_daily_bars(ticker, days=days)
        if len(bars) < 10:
            continue
        series[ticker] = bars.set_index("date")["close"].pct_change().dropna()
    return pd.DataFrame(series).dropna(how="all")


async def compute_advanced_risk() -> dict:
    portfolio = demo_portfolio()
    tickers = list(portfolio["positions"].keys())
    all_tickers = list(dict.fromkeys(tickers + ["QQQ", "SPY"]))
    returns = await _returns_matrix(all_tickers)

    var_95 = 0.0
    max_dd = portfolio["max_drawdown_est"]
    correlation: dict[str, dict[str, float]] = {}
    stress: list[dict] = []

    if not returns.empty and len(returns) >= 20:
        weights = []
        weight_tickers = [t for t in tickers if t in returns.columns]
        if weight_tickers:
            total_w = sum(portfolio["positions"][t]["weight_pct"] for t in weight_tickers)
            for t in weight_tickers:
                weights.append(portfolio["positions"][t]["weight_pct"] / total_w)
            port_returns = returns[weight_tickers].dot(weights)
            var_95 = float(np.percentile(port_returns, 5) * portfolio["account_value"])

        corr = returns.corr().round(2)
        correlation = {col: corr[col].to_dict() for col in corr.columns}

        stress = [
            {
                "name": "Tech selloff -8%",
                "impact_usd": round(-portfolio["account_value"] * 0.08 * 0.72, 2),
                "severity": "high",
            },
            {
                "name": "QQQ -5% shock",
                "impact_usd": round(
                    -portfolio["account_value"]
                    * 0.05
                    * (portfolio["sector_exposure"].get("Technology", 40) / 100),
                    2,
                ),
                "severity": "medium",
            },
            {
                "name": "VIX spike +20%",
                "impact_usd": round(-portfolio["account_value"] * 0.03, 2),
                "severity": "medium",
            },
        ]

    return {
        "var_95_1d": round(var_95, 2),
        "max_drawdown_est": max_dd,
        "correlation_matrix": correlation,
        "stress_tests": stress,
        "tickers_analyzed": list(returns.columns) if not returns.empty else [],
        "data_provider": returns.attrs.get("provider", "mock"),
    }
