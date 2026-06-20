"""Risk engine — veto power over all trade decisions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.ml.scoring import score_ticker
from app.portfolio.demo import demo_portfolio
from app.risk.rules import RiskRules, default_rules
from app.services.features import compute_ticker_features

TECH_TICKERS = {"NVDA", "MSFT", "META", "AAPL", "GOOGL", "AMZN", "QQQ", "SMH", "GBTC", "TSLA"}


@dataclass
class RiskVerdict:
    verdict: str
    warnings: list[str]
    blocks: list[str]


def _in_no_trade_window(minutes: int) -> bool:
    if minutes <= 0:
        return False
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    window_end = market_open + timedelta(minutes=minutes)
    return market_open <= now < window_end


class RiskEngine:
    def __init__(self, rules: RiskRules | None = None):
        self.rules = rules or default_rules()

    def _daily_loss_blocks(self, portfolio: dict) -> list[str]:
        blocks: list[str] = []
        daily_pnl = float(portfolio.get("daily_pnl", 0))
        if daily_pnl <= -self.rules.max_daily_loss_usd:
            blocks.append(
                f"Daily loss ${abs(daily_pnl):.2f} hit the "
                f"${self.rules.max_daily_loss_usd:.2f} circuit breaker."
            )
        return blocks

    def evaluate_ticker(
        self,
        ticker: str,
        features: dict,
        scores: dict,
        portfolio: dict | None = None,
    ) -> RiskVerdict:
        warnings: list[str] = []
        blocks: list[str] = []

        portfolio = portfolio or demo_portfolio()
        blocks.extend(self._daily_loss_blocks(portfolio))

        if ticker not in self.rules.allowed_tickers:
            blocks.append(f"{ticker} is not in the allowed ticker list.")

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

        composite = float(scores.get("composite", 50))
        if composite < 35:
            warnings.append(f"Weak setup score ({composite:.0f}/100) — consider waiting.")
        risk_component = float(scores.get("components", {}).get("risk", 50))
        if risk_component < 40:
            warnings.append(f"Elevated volatility risk score ({risk_component:.0f}/100).")

        if blocks:
            verdict = "BLOCK"
        elif warnings:
            verdict = "CAUTION"
        else:
            verdict = "ALLOW"

        return RiskVerdict(verdict=verdict, warnings=warnings, blocks=blocks)

    async def preview_trade(
        self,
        ticker: str,
        side: str,
        quantity: float,
        limit_price: float,
        order_type: str = "limit",
        asset_type: str = "equity",
        portfolio: dict | None = None,
    ) -> dict:
        order_value = quantity * limit_price
        warnings: list[str] = []
        blocks: list[str] = []

        portfolio = portfolio or demo_portfolio()
        blocks.extend(self._daily_loss_blocks(portfolio))

        if asset_type in self.rules.blocked_asset_types:
            blocks.append(f"{asset_type} trades are blocked by policy.")

        if asset_type == "option" and not self.rules.allow_options:
            blocks.append("Options require explicit manual approval — blocked in Phase 1.")

        if _in_no_trade_window(self.rules.no_trade_first_minutes):
            blocks.append(
                f"No trades in the first {self.rules.no_trade_first_minutes} minutes after market open."
            )

        if ticker not in self.rules.allowed_tickers:
            blocks.append(f"{ticker} not in allowed list.")

        if order_value > self.rules.max_trade_usd:
            blocks.append(
                f"Order value ${order_value:.2f} exceeds max ${self.rules.max_trade_usd:.2f}."
            )

        if order_type == "market" and not self.rules.allow_market_orders:
            blocks.append("Market orders are blocked for volatile names — use limit orders.")

        features = await compute_ticker_features(ticker)
        scores = score_ticker(features, ticker)
        ticker_verdict = self.evaluate_ticker(ticker, features, scores, portfolio=portfolio)
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
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "limit_price": limit_price,
            "setup_label": scores["label"],
            "composite_score": scores["composite"],
        }

    async def portfolio_snapshot(self) -> dict:
        portfolio = demo_portfolio()
        tech_pct = portfolio["sector_exposure"].get("Technology", 0)
        alerts = []

        daily_pnl = float(portfolio.get("daily_pnl", 0))
        if daily_pnl <= -self.rules.max_daily_loss_usd:
            alerts.append(
                {
                    "severity": "high",
                    "title": "Daily Loss Limit",
                    "detail": (
                        f"Daily P&L ${daily_pnl:.2f} breached "
                        f"-${self.rules.max_daily_loss_usd:.2f} limit — new trades blocked."
                    ),
                }
            )

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
