"""Point-in-time ML feature snapshots for journal-augmented retraining."""

from __future__ import annotations

from app.ml.feature_builder import FEATURE_COLS


def build_ml_snapshot(features: dict, scores: dict | None = None) -> dict:
    """Capture feature vector + model metadata at trade decision time."""
    snapshot = {col: round(float(features.get(col, 0)), 4) for col in FEATURE_COLS}
    snapshot["ml_bullish_prob"] = round(float(features.get("ml_bullish_prob", 0.5)), 4)
    snapshot["ml_confidence"] = round(float(features.get("ml_confidence", 0)), 4)
    snapshot["ml_model_version"] = int(features.get("ml_model_version", 0))
    if scores:
        snapshot["composite_score"] = round(float(scores.get("composite", 0)), 2)
    return snapshot


def journal_target_from_trade(side: str, pnl: float) -> int:
    """Label: 1 if bullish direction matched trade outcome intent."""
    profitable = pnl > 0
    return int(profitable == (side.lower() == "buy"))
