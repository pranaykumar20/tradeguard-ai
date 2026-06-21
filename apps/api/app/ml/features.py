"""Legacy sync feature shim — prefer app.services.features.compute_ticker_features."""

import hashlib


def _seeded_float(ticker: str, salt: str, lo: float, hi: float) -> float:
    digest = hashlib.sha256(f"{ticker}:{salt}".encode()).hexdigest()
    n = int(digest[:8], 16) / 0xFFFFFFFF
    return lo + n * (hi - lo)


def compute_ticker_features(ticker: str) -> dict[str, float | str]:
    """Sync fallback for tests — production uses async service layer."""
    return {
        "last_price": round(_seeded_float(ticker, "price", 80, 520), 2),
        "price_vs_20dma": round(_seeded_float(ticker, "20dma", -5, 8), 2),
        "price_vs_50dma": round(_seeded_float(ticker, "50dma", -8, 12), 2),
        "rsi_14": round(_seeded_float(ticker, "rsi", 28, 78), 1),
        "macd_signal": round(_seeded_float(ticker, "macd", -2, 2), 2),
        "atr_percent": round(_seeded_float(ticker, "atr", 1.5, 6.5), 2),
        "volume_spike": round(_seeded_float(ticker, "vol", 0.6, 2.2), 2),
        "news_sentiment_score": round(_seeded_float(ticker, "news", 35, 85), 0),
        "qqq_trend": "bullish" if _seeded_float(ticker, "qqq", 0, 1) > 0.45 else "bearish",
        "qqq_trend_numeric": 1.0 if _seeded_float(ticker, "qqq", 0, 1) > 0.45 else 0.0,
        "vix_change": round(_seeded_float(ticker, "vix", -3, 8), 1),
        "regime_risk_adj": 0.0,
        "sector_strength": round(_seeded_float(ticker, "sector", 40, 90), 0),
        "ml_bullish_prob": round(_seeded_float(ticker, "ml", 0.35, 0.72), 2),
        "ml_confidence": round(_seeded_float(ticker, "mlconf", 0.1, 0.6), 2),
        "ml_direction": "bullish",
        "data_provider": "mock-sync",
    }
