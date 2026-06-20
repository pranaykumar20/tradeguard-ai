"""Macro regime detection — Phase 6.4."""

from app.core.config import settings
from app.services.features import compute_ticker_features


REGIME_LABELS = {
    "risk_on": "Risk-On",
    "neutral": "Neutral",
    "risk_off": "Risk-Off",
    "high_vol": "High Volatility",
}


class RegimeService:
    async def detect(self) -> dict:
        if not settings.regime_detection_enabled:
            return {
                "regime": "neutral",
                "label": REGIME_LABELS["neutral"],
                "enabled": False,
                "risk_score_adjustment": 0,
                "signals": {},
            }

        spy_features = await compute_ticker_features("SPY", use_cache=True)
        qqq_features = await compute_ticker_features("QQQ", use_cache=True)

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
            },
            "guidance": self._guidance(regime),
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
        return round(max(0.0, min(100.0, composite + adj)), 1)
