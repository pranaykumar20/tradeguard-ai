"""Risk rules — code-based guardrails, not prompt-based."""

from pydantic import BaseModel, Field


class RiskRules(BaseModel):
    max_trade_usd: float = 250.0
    max_daily_loss_usd: float = 50.0
    max_single_name_pct: float = 20.0
    max_tech_sector_pct: float = 30.0
    require_manual_approval: bool = True
    allow_options: bool = False
    allow_market_orders: bool = False
    no_trade_first_minutes: int = 10
    allowed_tickers: list[str] = Field(
        default_factory=lambda: ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"]
    )
    blocked_asset_types: list[str] = Field(default_factory=lambda: ["crypto_option"])


def default_rules() -> RiskRules:
    from app.core.config import settings

    return RiskRules(
        max_trade_usd=settings.risk_max_trade_usd,
        max_daily_loss_usd=settings.risk_max_daily_loss_usd,
        max_single_name_pct=settings.risk_max_single_name_pct,
        max_tech_sector_pct=settings.risk_max_tech_sector_pct,
        require_manual_approval=settings.risk_require_manual_approval,
        allow_options=settings.risk_allow_options,
    )
