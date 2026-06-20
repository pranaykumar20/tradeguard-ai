"""Risk engine — veto power over all trade decisions."""

from dataclasses import dataclass

from app.portfolio.demo import demo_portfolio
from app.risk.rules import RiskRules, default_rules

TECH_TICKERS = {"NVDA", "MSFT", "META", "AAPL", "GOOGL", "AMZN", "QQQ", "SMH", "GBTC"}


@dataclass
class RiskVerdict:
    verdict: str
    warnings: list[str]
    blocks: list[str]


class RiskEngine:
    def __init__(self, rules: RiskRules | None = None):
        self.rules = rules or default_rules()

    def evaluate_ticker(
        self,
        ticker: str,
        features: dict,
        scores: dict,
    ) -> RiskVerdict:
        warnings: list[str] = []
        blocks: list[str] = []

        if ticker not in self.rules.allowed_tickers:
            blocks.append(f"{ticker} is not in the allowed ticker list.")

        portfolio = demo_portfolio()
        tech_pct = portfolio["sector_exposure"].get("Technology", 0)
        if ticker in TECH_TICKERS and tech_pct >= self.rules.max_tech_sector_pct:
            warnings.append(
                f"Tech sector exposure is {tech_pct:.1f}% (limit {self.rules.max_tech_sector_pct:.0f}%)."
            )

        position_pct = portfolio["positions"].get(ticker, {}).get("weight_pct", 0)
        if position_pct >= self.rules.max_single_name_pct:
            blocks.append(
                f"{ticker} already at {position_pct:.1f}% of portfolio "
                f"(limit {self.rules.max_single_name_pct:.0f}%)."
            )

        vix_change = float(features.get("vix_change", 0))
        if vix_change > 5:
            warnings.append("VIX rising — elevated market volatility.")

        qqq_trend = str(features.get("qqq_trend", "neutral"))
        if qqq_trend == "bearish" and ticker in TECH_TICKERS:
            warnings.append("QQQ trend is bearish — tech adds carry higher risk.")

        rsi = float(features.get("rsi_14", 50))
        if rsi > 75:
            warnings.append(f"RSI overbought at {rsi:.0f}.")

        if blocks:
            verdict = "BLOCK"
        elif warnings:
            verdict = "CAUTION"
        else:
            verdict = "ALLOW"

        return RiskVerdict(verdict=verdict, warnings=warnings, blocks=blocks)

    def preview_trade(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float,
        order_type: str = "limit",
    ) -> dict:
        order_value = quantity * limit_price
        warnings: list[str] = []
        blocks: list[str] = []

        if ticker not in self.rules.allowed_tickers:
            blocks.append(f"{ticker} not in allowed list.")

        if order_value > self.rules.max_trade_usd:
            blocks.append(
                f"Order value ${order_value:.2f} exceeds max ${self.rules.max_trade_usd:.2f}."
            )

        if order_type == "market" and not self.rules.allow_market_orders:
            blocks.append("Market orders are blocked for volatile names — use limit orders.")

        features = {"rsi_14": 58, "qqq_trend": "neutral", "vix_change": 2}
        scores = {"composite": 65, "label": "Watch", "components": {}}
        ticker_verdict = self.evaluate_ticker(ticker, features, scores)
        warnings.extend(ticker_verdict.warnings)
        blocks.extend(ticker_verdict.blocks)

        allowed = len(blocks) == 0
        verdict = "BLOCK" if blocks else ("CAUTION" if warnings else "ALLOW")

        return {
            "allowed": allowed,
            "verdict": verdict,
            "order_value": round(order_value, 2),
            "warnings": warnings,
            "blocks": blocks,
            "requires_approval": self.rules.require_manual_approval,
        }

    async def portfolio_snapshot(self) -> dict:
        portfolio = demo_portfolio()
        tech_pct = portfolio["sector_exposure"].get("Technology", 0)
        alerts = []

        if tech_pct > self.rules.max_tech_sector_pct:
            alerts.append(
                {
                    "severity": "high",
                    "title": "Sector Overweight",
                    "detail": f"Technology at {tech_pct:.1f}% vs limit {self.rules.max_tech_sector_pct:.0f}%.",
                }
            )

        for ticker, pos in portfolio["positions"].items():
            if pos["weight_pct"] > self.rules.max_single_name_pct:
                alerts.append(
                    {
                        "severity": "high",
                        "title": "High Concentration",
                        "detail": f"{ticker} is {pos['weight_pct']:.1f}% of portfolio.",
                    }
                )

        risk_score = min(100, int(40 + tech_pct + portfolio.get("beta", 1) * 10))
        label = "Low" if risk_score < 40 else "Moderate" if risk_score < 65 else "Elevated"

        return {
            "risk_score": risk_score,
            "risk_label": label,
            "portfolio_value": portfolio["account_value"],
            "daily_pnl": portfolio["daily_pnl"],
            "beta": portfolio["beta"],
            "max_drawdown_est": portfolio["max_drawdown_est"],
            "diversification": portfolio["diversification"],
            "cash_pct": portfolio["cash_pct"],
            "sector_exposure": portfolio["sector_exposure"],
            "alerts": alerts,
        }
