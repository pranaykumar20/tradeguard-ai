"""Cached model inference — load once, predict many."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.core.config import settings
from app.ml.feature_builder import FEATURE_COLS

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "models" / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "direction_model.joblib"
META_PATH = ARTIFACTS_DIR / "model_meta.json"
HISTORY_PATH = ARTIFACTS_DIR / "model_history.json"

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
        "journal_trades_used": 0,
        "deploy_gate_passed": False,
        "feature_importance": {},
    }


def load_meta() -> dict:
    global _meta
    if _meta is not None:
        return _meta
    if META_PATH.exists():
        _meta = json.loads(META_PATH.read_text())
        return _meta
    _meta = _default_meta()
    return _meta


def save_meta(meta: dict) -> dict:
    global _meta
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2))
    _meta = meta
    return meta


def reload_model() -> None:
    global _model, _meta
    _model = None
    _meta = None
    load_meta()
    get_model()


def get_model() -> Any | None:
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        return None
    _model = joblib.load(MODEL_PATH)
    return _model


def model_exists() -> bool:
    return MODEL_PATH.exists()


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    return json.loads(HISTORY_PATH.read_text())


def _save_history(entries: list[dict]) -> list[dict]:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(entries, indent=2))
    return entries


def archive_current_model() -> dict | None:
    """Copy active model + meta to versioned files before deploy."""
    if not MODEL_PATH.exists():
        return None

    meta = load_meta()
    version = int(meta.get("version", 0))
    if version <= 0:
        return None

    archive_model = ARTIFACTS_DIR / f"direction_model_v{version}.joblib"
    archive_meta = ARTIFACTS_DIR / f"model_meta_v{version}.json"
    shutil.copy2(MODEL_PATH, archive_model)
    if META_PATH.exists():
        shutil.copy2(META_PATH, archive_meta)

    history = _load_history()
    if not any(entry.get("version") == version for entry in history):
        history.append(
            {
                "version": version,
                "model_type": meta.get("model_type"),
                "auc": meta.get("auc"),
                "accuracy": meta.get("accuracy"),
                "brier": meta.get("brier"),
                "source": meta.get("source"),
                "last_trained_at": meta.get("last_trained_at"),
                "journal_trades_used": meta.get("journal_trades_used", 0),
                "archived_at": meta.get("last_trained_at"),
            }
        )
        history.sort(key=lambda e: int(e.get("version", 0)), reverse=True)
        max_versions = max(2, settings.ml_max_history_versions)
        _save_history(history[:max_versions])
    return {"version": version, "path": str(archive_model)}


def list_model_history() -> list[dict]:
    history = _load_history()
    active = load_meta()
    active_version = int(active.get("version", 0))
    enriched = []
    for entry in history:
        version = int(entry.get("version", 0))
        archive_model = ARTIFACTS_DIR / f"direction_model_v{version}.joblib"
        enriched.append(
            {
                **entry,
                "active": version == active_version,
                "artifact_exists": archive_model.exists(),
            }
        )
    return enriched


def rollback_to_version(version: int) -> dict:
    archive_model = ARTIFACTS_DIR / f"direction_model_v{version}.joblib"
    archive_meta = ARTIFACTS_DIR / f"model_meta_v{version}.json"
    if not archive_model.exists():
        return {"status": "error", "reason": "version_not_found", "version": version}

    current = load_meta()
    if int(current.get("version", 0)) > 0 and MODEL_PATH.exists():
        archive_current_model()

    shutil.copy2(archive_model, MODEL_PATH)
    if archive_meta.exists():
        shutil.copy2(archive_meta, META_PATH)
    else:
        save_meta({**current, "version": version, "rolled_back": True})

    reload_model()
    return {"status": "ok", "version": version, "meta": load_meta()}


def _direction_label(prob: float) -> str:
    if prob >= 0.55:
        return "bullish"
    if prob <= 0.45:
        return "bearish"
    return "neutral"


def predict_direction(features: np.ndarray) -> dict:
    """Return bullish probability, confidence, and direction label."""
    model = get_model()
    vector = np.asarray(features, dtype=float).reshape(1, -1)
    if model is None or vector.shape[1] != len(FEATURE_COLS):
        return {"prob": 0.5, "confidence": 0.0, "direction": "neutral", "version": 0}

    proba = model.predict_proba(vector)[0]
    prob = float(proba[1]) if len(proba) > 1 else 0.5
    confidence = abs(prob - 0.5) * 2
    meta = load_meta()
    return {
        "prob": prob,
        "confidence": confidence,
        "direction": _direction_label(prob),
        "version": int(meta.get("version", 0)),
    }


def predict_direction_prob(features: np.ndarray) -> float:
    """Backward-compatible float probability."""
    return predict_direction(features)["prob"]
