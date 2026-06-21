"""Volatility/regime classifier training."""

from __future__ import annotations

from datetime import datetime, timezone

import joblib
import pandas as pd

from app.core.config import settings
from app.ml.training import _build_model, _feature_importance, _model_type_name, walk_forward_metrics
from app.ml.volatility_builder import TARGET_VOL_COL, VOL_FEATURE_COLS
from app.ml.volatility_registry import VOL_MODEL_PATH, load_vol_meta, reload_vol_model, save_vol_meta


def train_volatility_model(
    df: pd.DataFrame,
    *,
    source: str = "macro",
    force_deploy: bool = False,
) -> dict:
    cols = VOL_FEATURE_COLS
    if df.empty or len(df) < settings.ml_min_samples:
        return {"status": "skipped", "reason": "insufficient training data", "samples": len(df)}

    if df[TARGET_VOL_COL].nunique() < 2:
        return {"status": "skipped", "reason": "single_class_target", "samples": len(df)}

    wf = walk_forward_metrics(df, cols, target_col=TARGET_VOL_COL)
    prev = load_vol_meta()
    prev_auc = float(prev.get("auc") or 0.0)
    new_auc = float(wf.get("auc") or 0.0)
    gate_passed = force_deploy or prev_auc == 0 or new_auc >= prev_auc - settings.ml_min_auc_delta

    if not gate_passed:
        return {
            "status": "skipped",
            "reason": "deploy_gate_failed",
            "previous_auc": prev_auc,
            "new_auc": new_auc,
            "walk_forward": wf,
            "deploy_gate_passed": False,
        }

    model = _build_model()
    model.fit(df[cols], df[TARGET_VOL_COL])
    VOL_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, VOL_MODEL_PATH)

    version = int(prev.get("version", 0)) + 1
    meta = {
        "version": version,
        "model_type": _model_type_name(model),
        "last_trained_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "accuracy": wf.get("accuracy"),
        "auc": new_auc,
        "brier": wf.get("brier"),
        "deploy_gate_passed": True,
        "feature_importance": _feature_importance(model, cols),
        "walk_forward_folds": wf.get("folds"),
        "samples": wf.get("samples"),
    }
    save_vol_meta(meta)
    reload_vol_model()

    return {
        "status": "ok",
        "version": version,
        "accuracy": wf.get("accuracy"),
        "auc": new_auc,
        "brier": wf.get("brier"),
        "model_type": meta["model_type"],
        "deploy_gate_passed": True,
        "walk_forward": wf,
        "feature_importance": meta["feature_importance"],
    }
