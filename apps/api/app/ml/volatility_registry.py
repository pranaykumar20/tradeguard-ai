"""Cached volatility/regime classifier inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.ml.volatility_builder import VOL_FEATURE_COLS

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "models" / "artifacts"
VOL_MODEL_PATH = ARTIFACTS_DIR / "volatility_model.joblib"
VOL_META_PATH = ARTIFACTS_DIR / "volatility_meta.json"

_model: Any | None = None
_meta: dict | None = None


def _default_meta() -> dict:
    return {
        "version": 0,
        "model_type": "none",
        "last_trained_at": None,
        "accuracy": None,
        "auc": None,
        "brier": None,
        "source": "none",
        "deploy_gate_passed": False,
        "feature_importance": {},
    }


def load_vol_meta() -> dict:
    global _meta
    if _meta is not None:
        return _meta
    if VOL_META_PATH.exists():
        _meta = json.loads(VOL_META_PATH.read_text())
        return _meta
    _meta = _default_meta()
    return _meta


def save_vol_meta(meta: dict) -> dict:
    global _meta
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    VOL_META_PATH.write_text(json.dumps(meta, indent=2))
    _meta = meta
    return meta


def reload_vol_model() -> None:
    global _model, _meta
    _model = None
    _meta = None
    load_vol_meta()
    get_vol_model()


def get_vol_model() -> Any | None:
    global _model
    if _model is not None:
        return _model
    if not VOL_MODEL_PATH.exists():
        return None
    _model = joblib.load(VOL_MODEL_PATH)
    return _model


def vol_model_exists() -> bool:
    return VOL_MODEL_PATH.exists()


def predict_volatility(features: np.ndarray) -> dict:
    model = get_vol_model()
    vector = np.asarray(features, dtype=float).reshape(1, -1)
    if model is None or vector.shape[1] != len(VOL_FEATURE_COLS):
        return {
            "prob": 0.5,
            "confidence": 0.0,
            "regime_hint": "neutral",
            "version": 0,
        }

    proba = model.predict_proba(vector)[0]
    prob = float(proba[1]) if len(proba) > 1 else 0.5
    confidence = abs(prob - 0.5) * 2
    meta = load_vol_meta()

    if prob >= 0.6:
        regime_hint = "high_vol"
    elif prob <= 0.35:
        regime_hint = "calm"
    else:
        regime_hint = "neutral"

    return {
        "prob": prob,
        "confidence": confidence,
        "regime_hint": regime_hint,
        "version": int(meta.get("version", 0)),
    }
