"""Bootstrap ML model on mock market data if no artifact exists."""

from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from app.ml.training import ARTIFACTS_DIR, train_direction_model
from app.providers.market.factory import get_market_data_provider
from app.providers.market.mock import MockMarketDataProvider

logger = structlog.get_logger()

BOOTSTRAP_TICKERS = ["NVDA", "MSFT", "META", "TSLA", "QQQ", "GBTC"]


async def ensure_direction_model() -> dict | None:
    path = ARTIFACTS_DIR / "direction_model.joblib"
    if path.exists():
        return None

    provider = get_market_data_provider()
    mock = MockMarketDataProvider()
    rows = []

    for ticker in BOOTSTRAP_TICKERS:
        bars = await provider.get_daily_bars(ticker, days=180)
        if len(bars) < 60:
            bars = await mock.get_daily_bars(ticker, days=180)
        close = bars["close"]
        ret5 = close.pct_change(5).shift(-5)
        df = pd.DataFrame(
            {
                "price_vs_20dma": (close - close.rolling(20).mean()) / close.rolling(20).mean() * 100,
                "price_vs_50dma": (close - close.rolling(50).mean()) / close.rolling(50).mean() * 100,
                "rsi_14": close.pct_change().rolling(14).std() * 100,
                "macd_signal": close.diff().rolling(5).mean(),
                "atr_percent": (close.rolling(14).max() - close.rolling(14).min()) / close * 100,
                "volume_spike": bars["volume"] / bars["volume"].rolling(20).mean(),
                "target_up_5d": (ret5 > 0).astype(int),
            }
        ).dropna()
        df["ticker"] = ticker
        rows.append(df)

    if not rows:
        return None

    dataset = pd.concat(rows, ignore_index=True)
    feature_cols = [
        "price_vs_20dma",
        "price_vs_50dma",
        "rsi_14",
        "macd_signal",
        "atr_percent",
        "volume_spike",
    ]
    metrics = train_direction_model(dataset, feature_cols=feature_cols)
    logger.info("ml_model_bootstrapped", accuracy=metrics.get("accuracy"))
    return metrics
