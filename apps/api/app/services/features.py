"""Feature engineering from market data provider (mock or Polygon)."""

from __future__ import annotations

from app.core.config import settings
from app.db.storage import get_storage
from app.ml.feature_builder import (
    feature_vector_from_dict,
    latest_feature_row,
    macro_from_qqq_bars,
    qqq_trend_to_numeric,
)
from app.ml.model_registry import predict_direction
from app.providers.market.factory import get_market_data_provider
from app.services.news import NewsService

_news = NewsService()


async def _regime_risk_adj() -> float:
    try:
        from app.services.regime import RegimeService

        regime = await RegimeService().detect()
        if regime.get("enabled"):
            return float(regime.get("risk_score_adjustment", 0))
    except Exception:
        pass
    return 0.0


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
    qqq_trend, vix_change = macro_from_qqq_bars(qqq_bars)

    news_sentiment = await _news.sentiment_score(ticker)
    regime_adj = await _regime_risk_adj()

    row = latest_feature_row(
        bars,
        news_sentiment=news_sentiment,
        qqq_trend=qqq_trend,
        vix_change=vix_change,
        regime_risk_adj=regime_adj,
    )
    ml_result = predict_direction(feature_vector_from_dict(row))
    row["ml_bullish_prob"] = round(float(ml_result["prob"]), 2)
    row["ml_confidence"] = round(float(ml_result["confidence"]), 2)
    row["ml_direction"] = ml_result["direction"]
    row["data_provider"] = settings.active_market_provider

    await storage.cache_features(ticker, row, provider.provider_name)
    return row


async def refresh_all_tickers(tickers: list[str]) -> dict[str, dict]:
    results = {}
    for ticker in tickers:
        results[ticker] = await compute_ticker_features(ticker, use_cache=False)
    return results
