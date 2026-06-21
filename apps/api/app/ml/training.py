"""ML model training — XGBoost with walk-forward validation."""

from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score

from app.core.config import settings
from app.ml.feature_builder import FEATURE_COLS, TARGET_COL
from app.ml.model_registry import MODEL_PATH, archive_current_model, load_meta, reload_model, save_meta

# Re-export for callers
ARTIFACTS_DIR = MODEL_PATH.parent


def _build_model() -> Any:
    model_type = settings.ml_model_type.lower()
    if model_type == "xgboost":
        try:
            from xgboost import XGBClassifier

            return XGBClassifier(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
                random_state=42,
                n_jobs=-1,
            )
        except Exception:
            pass
    return RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42, n_jobs=-1)


def _model_type_name(model: Any) -> str:
    name = type(model).__name__.lower()
    if "xgb" in name:
        return "xgboost"
    return "random_forest"


def _evaluate_split(model: Any, test: pd.DataFrame, cols: list[str], target_col: str = TARGET_COL) -> dict:
    if test.empty:
        return {"accuracy": 0.0, "auc": 0.5, "brier": 0.25, "samples": 0}

    preds = model.predict(test[cols])
    proba = model.predict_proba(test[cols])[:, 1]
    y = test[target_col]

    metrics: dict = {
        "accuracy": float(accuracy_score(y, preds)),
        "brier": float(brier_score_loss(y, proba)),
        "samples": int(len(test)),
    }
    try:
        metrics["auc"] = float(roc_auc_score(y, proba))
    except ValueError:
        metrics["auc"] = 0.5
    return metrics


def walk_forward_metrics(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    *,
    target_col: str = TARGET_COL,
) -> dict:
    """Expanding-window walk-forward evaluation."""
    cols = feature_cols or FEATURE_COLS
    folds = max(2, settings.ml_walk_forward_folds)
    n = len(df)
    if n < settings.ml_min_samples:
        return {"accuracy": 0.0, "auc": 0.5, "brier": 0.25, "folds": 0, "samples": n}

    fold_size = max(10, n // (folds + 1))
    fold_metrics: list[dict] = []

    for i in range(1, folds + 1):
        train_end = fold_size * i
        test_end = min(train_end + fold_size, n)
        if train_end < 20 or test_end <= train_end:
            continue
        train = df.iloc[:train_end]
        test = df.iloc[train_end:test_end]
        if test[target_col].nunique() < 2:
            continue
        model = _build_model()
        model.fit(train[cols], train[target_col])
        fold_metrics.append(_evaluate_split(model, test, cols, target_col))

    if not fold_metrics:
        model = _build_model()
        split_idx = int(n * 0.8)
        train, test = df.iloc[:split_idx], df.iloc[split_idx:]
        model.fit(train[cols], train[target_col])
        single = _evaluate_split(model, test, cols, target_col)
        single["folds"] = 1
        single["samples"] = n
        return single

    return {
        "accuracy": float(np.mean([m["accuracy"] for m in fold_metrics])),
        "auc": float(np.mean([m["auc"] for m in fold_metrics])),
        "brier": float(np.mean([m["brier"] for m in fold_metrics])),
        "folds": len(fold_metrics),
        "samples": n,
        "fold_details": fold_metrics,
    }


def _feature_importance(model: Any, cols: list[str]) -> dict[str, float]:
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
        pairs = sorted(zip(cols, values, strict=False), key=lambda x: x[1], reverse=True)
        return {k: round(float(v), 4) for k, v in pairs[:5]}
    return {}


def train_direction_model(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    *,
    source: str = "market_only",
    journal_trades_used: int = 0,
    force_deploy: bool = False,
) -> dict:
    """Train on full dataset after walk-forward eval; deploy if gate passes."""
    cols = feature_cols or FEATURE_COLS
    if df.empty or len(df) < settings.ml_min_samples:
        return {"status": "skipped", "reason": "insufficient training data", "samples": len(df)}

    wf = walk_forward_metrics(df, cols)
    prev = load_meta()
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
    model.fit(df[cols], df[TARGET_COL])
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if int(prev.get("version", 0)) > 0:
        archive_current_model()
    joblib.dump(model, MODEL_PATH)

    version = int(prev.get("version", 0)) + 1
    from datetime import datetime, timezone

    meta = {
        "version": version,
        "model_type": _model_type_name(model),
        "last_trained_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "accuracy": wf.get("accuracy"),
        "auc": new_auc,
        "brier": wf.get("brier"),
        "journal_trades_used": journal_trades_used,
        "deploy_gate_passed": True,
        "feature_importance": _feature_importance(model, cols),
        "walk_forward_folds": wf.get("folds"),
        "samples": wf.get("samples"),
    }
    save_meta(meta)
    reload_model()

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
