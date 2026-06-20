"""Multi-factor scoring — combines technical, macro, sentiment, ML signals."""

from app.ml.features import compute_ticker_features


WEIGHTS = {
    "technical": 0.30,
    "fundamental": 0.20,
    "news": 0.15,
    "macro": 0.15,
    "ml": 0.10,
    "risk": 0.10,
}


def _clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def score_ticker(features: dict | None = None, ticker: str = "") -> dict:
    if features is None:
        features = compute_ticker_features(ticker)

    rsi = float(features["rsi_14"])
    technical = _clamp(50 + float(features["price_vs_20dma"]) * 3 + (rsi - 50) * 0.4)
    fundamental = _clamp(float(features.get("sector_strength", 60)))
    news = _clamp(float(features["news_sentiment_score"]))
    macro = _clamp(
        70 if features["qqq_trend"] == "bullish" else 40,
        20,
        80,
    )
    ml = _clamp(float(features["ml_bullish_prob"]) * 100)
    risk = _clamp(100 - float(features["atr_percent"]) * 8 - max(0, float(features["vix_change"]) * 3))

    components = {
        "technical": round(technical, 1),
        "fundamental": round(fundamental, 1),
        "news": round(news, 1),
        "macro": round(macro, 1),
        "ml": round(ml, 1),
        "risk": round(risk, 1),
    }

    composite = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    composite = round(composite, 1)

    if composite >= 75:
        label = "Strong Buy Setup"
    elif composite >= 62:
        label = "Buy Setup"
    elif composite >= 48:
        label = "Watch"
    elif composite >= 35:
        label = "Avoid"
    else:
        label = "Sell / Reduce"

    return {"composite": composite, "label": label, "components": components}
