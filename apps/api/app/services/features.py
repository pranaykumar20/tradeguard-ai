"""Feature engineering from market data provider (mock or Polygon)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import ta

from app.core.config import settings
from app.db.storage import get_storage
from app.ml.training import predict_direction
from app.providers.market.factory import get_market_data_provider
from app.services.news import NewsService

_news = NewsService()


def _bars_to_features(
    ticker: str, bars: pd.DataFrame, qqq_trend: str, vix_change: float, news_sentiment: float
) -> dict:
    close = bars["close"]
    high = bars["high"]
    low = bars["low"]
    volume = bars["volume"]

    rsi = float(ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1])
    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma20
    last = float(close.iloc[-1])
    macd = ta.trend.MACD(close)
    macd_signal = float(macd.macd_diff().iloc[-1])
    atr = float(ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1])
    atr_pct = (atr / last * 100) if last else 0.0
    vol_mean = volume.rolling(20).mean().iloc[-1]
    vol_spike = float(volume.iloc[-1] / vol_mean) if vol_mean else 1.0

    feature_vector = np.array(
        [
            (last - sma20) / sma20 * 100 if sma20 else 0,
            (last - sma50) / sma50 * 100 if sma50 else 0,
            rsi,
            macd_signal,
            atr_pct,
            vol_spike,
        ]
    )
    ml_prob = predict_direction(feature_vector)

    return {
        "last_price": round(last, 2),
        "price_vs_20dma": round((last - sma20) / sma20 * 100 if sma20 else 0, 2),
        "price_vs_50dma": round((last - sma50) / sma50 * 100 if sma50 else 0, 2),
        "rsi_14": round(rsi, 1),
        "macd_signal": round(macd_signal, 2),
        "atr_percent": round(atr_pct, 2),
        "volume_spike": round(vol_spike, 2),
        "news_sentiment_score": round(news_sentiment, 1),
        "qqq_trend": qqq_trend,
        "vix_change": round(vix_change, 1),
        "sector_strength": round(min(95, max(35, 55 + feature_vector[0])), 0),
        "ml_bullish_prob": round(float(ml_prob), 2),
        "data_provider": settings.active_market_provider,
    }


async def compute_ticker_features(ticker: str, use_cache: bool = True) -> dict[str, float | str]:
    ticker = ticker.upper()
    storage = await get_storage()

    if use_cache:
        cached = await storage.get_cached_features(ticker)
        if cached:
            return cached

    provider = get_market_data_provider()
    bars = await provider.get_daily_bars(ticker, days=120)
    qqq_bars = await provider.get_macro_bars("QQQ", days=60)
    qqq_close = qqq_bars["close"]
    qqq_sma = qqq_close.rolling(20).mean().iloc[-1]
    qqq_last = float(qqq_close.iloc[-1])
    qqq_trend = "bullish" if qqq_last >= qqq_sma else "bearish"

    # Mock VIX proxy from QQQ volatility
    qqq_ret = qqq_close.pct_change().dropna()
    vix_change = float(qqq_ret.tail(5).std() * 100 * 10) if len(qqq_ret) > 5 else 2.0

    news_sentiment = await _news.sentiment_score(ticker)
    features = _bars_to_features(ticker, bars, qqq_trend, vix_change, news_sentiment)
    await storage.cache_features(ticker, features, provider.provider_name)
    return features


async def refresh_all_tickers(tickers: list[str]) -> dict[str, dict]:
    results = {}
    for ticker in tickers:
        results[ticker] = await compute_ticker_features(ticker, use_cache=False)
    return results
