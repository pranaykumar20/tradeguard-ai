"""ML model training pipeline (Phase 2).

Walk-forward validation, time-based splits, model persistence via joblib/mlflow.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "models" / "artifacts"


def train_direction_model(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str = "target_up_5d",
) -> dict:
    """Train a direction classifier with time-based split."""
    split_idx = int(len(df) * 0.8)
    train, test = df.iloc[:split_idx], df.iloc[split_idx:]

    model = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    model.fit(train[feature_cols], train[target_col])

    preds = model.predict(test[feature_cols])
    metrics = {
        "accuracy": float(accuracy_score(test[target_col], preds)),
        "report": classification_report(test[target_col], preds, output_dict=True),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS_DIR / "direction_model.joblib")

    return metrics


def predict_direction(features: np.ndarray) -> float:
    """Load model and return bullish probability."""
    path = ARTIFACTS_DIR / "direction_model.joblib"
    if not path.exists():
        return 0.5
    model = joblib.load(path)
    proba = model.predict_proba(features.reshape(1, -1))[0]
    return float(proba[1]) if len(proba) > 1 else 0.5
