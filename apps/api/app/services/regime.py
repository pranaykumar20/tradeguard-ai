"""Macro regime detection — Phase 6.4 + ML volatility classifier."""

from app.core.config import settings
from app.ml.volatility_builder import (
    latest_volatility_features,
    macro_context_from_bars,
    qqq_trend_to_numeric,
    volatility_vector_from_dict,
)
from app.ml.volatility_registry import predict_volatility
from app.providers.market.factory import get_market_data_provider
from app.providers.market.mock import MockMarketDataProvider
from app.services.features import compute_ticker_features


REGIME_LABELS = {
    "risk_on": "Risk-On",
    "neutral": "Neutral",
    "risk_off": "Risk-Off",
    "high_vol": "High Volatility",
}


class RegimeService:
    async def _ml_vol_prediction(self) -> dict:
        if not settings.ml_volatility_enabled:
            return {"prob": 0.5, "confidence": 0.0, "regime_hint": "neutral", "version": 0}

        provider = get_market_data_provider()
        mock = MockMarketDataProvider()
        spy_bars = await provider.get_macro_bars("SPY", days=120)
        if len(spy_bars) < 60:
            spy_bars = await mock.get_macro_bars("SPY", days=120)
        qqq_bars = await provider.get_macro_bars("QQQ", days=60)
        if len(qqq_bars) < 20:
            qqq_bars = await mock.get_macro_bars("QQQ", days=60)

        qqq_trend, vix_change = macro_context_from_bars(qqq_bars)
        row = latest_volatility_features(spy_bars, qqq_trend=qqq_trend, vix_change=vix_change)
        return predict_volatility(volatility_vector_from_dict(row))

    async def detect(self) -> dict:
        if not settings.regime_detection_enabled:
            return {
                "regime": "neutral",
                "label": REGIME_LABELS["neutral"],
                "enabled": False,
                "risk_score_adjustment": 0,
                "signals": {},
                "ml_vol_prob": 0.5,
                "ml_vol_confidence": 0.0,
                "ml_vol_enabled": False,
            }

        spy_features = await compute_ticker_features("SPY", use_cache=True)
        qqq_features = await compute_ticker_features("QQQ", use_cache=True)
        ml_vol = await self._ml_vol_prediction()
        ml_vol_prob = float(ml_vol.get("prob", 0.5))
        ml_vol_confidence = float(ml_vol.get("confidence", 0.0))

        vix_proxy = float(spy_features.get("vix_change", 2.0))
        qqq_trend = str(qqq_features.get("qqq_trend", "neutral"))
        spy_rsi = float(spy_features.get("rsi_14", 50))
        atr_pct = float(spy_features.get("atr_percent", 2.0))

        if vix_proxy >= 6.0 or atr_pct >= 4.5:
            regime = "high_vol"
            adjustment = -8
        elif qqq_trend == "bearish" or spy_rsi < 42:
            regime = "risk_off"
            adjustment = -5
        elif qqq_trend == "bullish" and vix_proxy < 3.0 and spy_rsi > 55:
            regime = "risk_on"
            adjustment = 3
        else:
            regime = "neutral"
            adjustment = 0

        if settings.ml_volatility_enabled and ml_vol_prob >= settings.ml_vol_high_threshold:
            if regime in {"neutral", "risk_on"}:
                regime = "high_vol"
                adjustment = min(adjustment, -8)
            elif regime == "risk_off":
                adjustment = min(adjustment, -8)

        return {
            "regime": regime,
            "label": REGIME_LABELS[regime],
            "enabled": True,
            "risk_score_adjustment": adjustment,
            "signals": {
                "vix_proxy": round(vix_proxy, 2),
                "qqq_trend": qqq_trend,
                "spy_rsi": round(spy_rsi, 1),
                "spy_atr_pct": round(atr_pct, 2),
                "qqq_trend_numeric": qqq_trend_to_numeric(qqq_trend),
            },
            "guidance": self._guidance(regime),
            "ml_vol_prob": round(ml_vol_prob, 3),
            "ml_vol_confidence": round(ml_vol_confidence, 3),
            "ml_vol_regime_hint": ml_vol.get("regime_hint", "neutral"),
            "ml_vol_version": int(ml_vol.get("version", 0)),
            "ml_vol_enabled": settings.ml_volatility_enabled,
        }

    @staticmethod
    def _guidance(regime: str) -> str:
        return {
            "risk_on": "Favorable macro — standard position sizes OK if risk rules pass.",
            "neutral": "Mixed signals — prefer limit orders and smaller adds.",
            "risk_off": "Defensive regime — favor quality, reduce new tech adds.",
            "high_vol": "Elevated volatility — tighten size, expect wider stops, manual approval.",
        }.get(regime, "")

    def apply_to_score(self, composite: float, regime_data: dict) -> float:
        adj = float(regime_data.get("risk_score_adjustment", 0))
        vol_penalty = 0.0
        if settings.ml_volatility_enabled:
            vol_prob = float(regime_data.get("ml_vol_prob", 0))
            vol_penalty = vol_prob * settings.ml_vol_score_penalty
        return round(max(0.0, min(100.0, composite + adj - vol_penalty)), 1)
