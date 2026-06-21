"""Bootstrap ML models on market data if no artifacts exist."""

import structlog

import pandas as pd

from app.ml.feature_builder import build_training_frame, macro_from_qqq_bars, qqq_trend_to_numeric
from app.ml.model_registry import model_exists
from app.ml.training import train_direction_model
from app.ml.volatility_builder import build_volatility_training_frame
from app.ml.volatility_registry import vol_model_exists
from app.ml.volatility_training import train_volatility_model
from app.providers.market.factory import get_market_data_provider
from app.providers.market.mock import MockMarketDataProvider

logger = structlog.get_logger()

BOOTSTRAP_TICKERS = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"]
MACRO_TICKERS = ["SPY", "QQQ"]


async def _macro_context(provider, mock):
    qqq_bars = await provider.get_macro_bars("QQQ", days=60)
    if len(qqq_bars) < 20:
        qqq_bars = await mock.get_macro_bars("QQQ", days=60)
    qqq_trend, vix_change = macro_from_qqq_bars(qqq_bars)
    return qqq_trend, vix_change, qqq_trend_to_numeric(qqq_trend)


async def ensure_direction_model() -> dict | None:
    if model_exists():
        return None

    provider = get_market_data_provider()
    mock = MockMarketDataProvider()
    qqq_trend, vix_change, qqq_num = await _macro_context(provider, mock)

    rows = []
    for ticker in BOOTSTRAP_TICKERS:
        bars = await provider.get_daily_bars(ticker, days=180)
        if len(bars) < 60:
            bars = await mock.get_daily_bars(ticker, days=180)
        frame = build_training_frame(
            bars,
            ticker=ticker,
            news_sentiment=50.0,
            qqq_trend_numeric=qqq_num,
            vix_change=vix_change,
            regime_risk_adj=0.0,
        )
        if not frame.empty:
            rows.append(frame)

    if not rows:
        return None

    dataset = pd.concat(rows, ignore_index=True)
    result = train_direction_model(dataset, source="bootstrap", force_deploy=True)
    logger.info("ml_model_bootstrapped", status=result.get("status"), auc=result.get("auc"))
    return result


async def ensure_volatility_model() -> dict | None:
    if vol_model_exists():
        return None

    provider = get_market_data_provider()
    mock = MockMarketDataProvider()
    qqq_trend, vix_change, qqq_num = await _macro_context(provider, mock)

    rows = []
    for ticker in MACRO_TICKERS:
        bars = await provider.get_macro_bars(ticker, days=180)
        if len(bars) < 60:
            bars = await mock.get_macro_bars(ticker, days=180)
        frame = build_volatility_training_frame(
            bars,
            ticker=ticker,
            qqq_trend_numeric=qqq_num,
            vix_change=vix_change,
        )
        if not frame.empty:
            rows.append(frame)

    if not rows:
        return None

    dataset = pd.concat(rows, ignore_index=True)
    result = train_volatility_model(dataset, source="bootstrap", force_deploy=True)
    logger.info("ml_vol_model_bootstrapped", status=result.get("status"), auc=result.get("auc"))
    return result
