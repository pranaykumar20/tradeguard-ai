"""Risk engine tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.risk.engine import RiskEngine, _in_no_trade_window
from app.risk.rules import RiskRules


from tests.helpers import MOCK_FEATURES


@pytest.mark.asyncio
async def test_blocks_oversized_trade():
    engine = RiskEngine(RiskRules(max_trade_usd=250, no_trade_first_minutes=0))
    with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_features:
        mock_features.return_value = MOCK_FEATURES.copy()
        result = await engine.preview_trade("NVDA", "buy", quantity=10, limit_price=50)
    assert result["allowed"] is False
    assert any("exceeds max" in b for b in result["blocks"])


@pytest.mark.asyncio
async def test_allows_small_limit_order_when_rules_pass():
    engine = RiskEngine(
        RiskRules(
            max_trade_usd=500,
            max_tech_sector_pct=50,
            max_single_name_pct=25,
            allowed_tickers=["NVDA"],
            no_trade_first_minutes=0,
        )
    )
    with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_features:
        mock_features.return_value = MOCK_FEATURES.copy()
        result = await engine.preview_trade("NVDA", "buy", quantity=1, limit_price=100)
    assert result["requires_approval"] is True
    assert "composite_score" in result


def test_blocks_disallowed_ticker():
    engine = RiskEngine(RiskRules(allowed_tickers=["NVDA"], no_trade_first_minutes=0))
    verdict = engine.evaluate_ticker(
        "AAPL",
        {"rsi_14": 50, "qqq_trend": "neutral", "vix_change": 1},
        {"composite": 60, "components": {"risk": 50}},
    )
    assert verdict.verdict == "BLOCK"


@pytest.mark.asyncio
async def test_blocks_market_order():
    engine = RiskEngine(RiskRules(allowed_tickers=["MSFT"], max_trade_usd=500, no_trade_first_minutes=0))
    with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_features:
        mock_features.return_value = MOCK_FEATURES.copy()
        result = await engine.preview_trade("MSFT", "buy", quantity=1, limit_price=100, order_type="market")
    assert result["allowed"] is False


@pytest.mark.asyncio
async def test_blocks_options():
    engine = RiskEngine(RiskRules(allowed_tickers=["NVDA"], max_trade_usd=500, no_trade_first_minutes=0))
    with patch("app.risk.engine.compute_ticker_features", new_callable=AsyncMock) as mock_features:
        mock_features.return_value = MOCK_FEATURES.copy()
        result = await engine.preview_trade(
            "NVDA", "buy", quantity=1, limit_price=100, asset_type="option"
        )
    assert result["allowed"] is False


def test_caution_on_high_tech_exposure():
    engine = RiskEngine(
        RiskRules(
            allowed_tickers=["TSLA"],
            max_tech_sector_pct=30,
            max_single_name_pct=25,
            no_trade_first_minutes=0,
        )
    )
    verdict = engine.evaluate_ticker(
        "TSLA",
        {"rsi_14": 55, "qqq_trend": "bullish", "vix_change": 2},
        {"composite": 65, "components": {"risk": 55}},
    )
    assert verdict.verdict == "CAUTION"


@pytest.mark.asyncio
async def test_daily_loss_circuit_breaker():
    engine = RiskEngine(RiskRules(max_daily_loss_usd=50, no_trade_first_minutes=0))
    with patch("app.risk.engine.demo_portfolio") as mock_portfolio, patch(
        "app.risk.engine.compute_ticker_features", new_callable=AsyncMock
    ) as mock_features:
        mock_portfolio.return_value = {
            "daily_pnl": -75.0,
            "sector_exposure": {"Technology": 10},
            "positions": {},
            "beta": 1.0,
        }
        mock_features.return_value = MOCK_FEATURES.copy()
        result = await engine.preview_trade("MSFT", "buy", quantity=1, limit_price=100)
    assert result["allowed"] is False
    assert any("Daily loss" in b for b in result["blocks"])


def test_no_trade_window_disabled_with_zero_minutes():
    assert _in_no_trade_window(0) is False
