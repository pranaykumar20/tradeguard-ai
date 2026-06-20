"""Risk engine tests."""

from app.risk.engine import RiskEngine
from app.risk.rules import RiskRules


def test_blocks_oversized_trade():
    engine = RiskEngine(RiskRules(max_trade_usd=250))
    result = engine.preview_trade("NVDA", "buy", quantity=10, limit_price=50)
    assert result["allowed"] is False
    assert any("exceeds max" in b for b in result["blocks"])


def test_allows_small_limit_order_when_rules_pass():
    engine = RiskEngine(
        RiskRules(
            max_trade_usd=500,
            max_tech_sector_pct=50,
            max_single_name_pct=25,
            allowed_tickers=["NVDA"],
        )
    )
    result = engine.preview_trade("NVDA", "buy", quantity=1, limit_price=100)
    assert result["requires_approval"] is True
