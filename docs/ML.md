# TradeGuard ML Pipeline

Direction model predicts **5-day bullish probability** for allowed tickers. It feeds composite scoring (18% weight) and hybrid risk CAUTION rules.

## Architecture

- **Features:** [`apps/api/app/ml/feature_builder.py`](../apps/api/app/ml/feature_builder.py) — shared train/inference formulas via `ta`
- **Training:** [`apps/api/app/ml/training.py`](../apps/api/app/ml/training.py) — XGBoost (default) + walk-forward CV
- **Inference:** [`apps/api/app/ml/model_registry.py`](../apps/api/app/ml/model_registry.py) — cached joblib model
- **Retrain:** `POST /api/intelligence/ml/retrain` + weekly Celery task

## Feature columns (10)

| Feature | Description |
|---------|-------------|
| price_vs_20dma | Price vs 20-day SMA (%) |
| price_vs_50dma | Price vs 50-day SMA (%) |
| rsi_14 | RSI(14) |
| macd_signal | MACD histogram |
| atr_percent | ATR as % of price |
| volume_spike | Volume / 20-day avg |
| news_sentiment_score | Ticker news sentiment |
| qqq_trend_numeric | 1 bullish / 0 bearish |
| vix_change | QQQ vol proxy |
| regime_risk_adj | Macro regime score adjustment |

## Hybrid risk rules

When previewing a trade, ML adds **CAUTION** warnings (never sole BLOCK):

- Buy + ML prob < 0.45 → model not bullish
- Sell + ML prob > 0.65 → model still bullish
- ML prob near 0.50 → low conviction
- Low confidence + bootstrap model → treat signal cautiously

Configure via `ML_BULLISH_BUY_MIN`, `ML_BULLISH_SELL_MAX`, `ML_LOW_CONFIDENCE_THRESHOLD`.

## Retrain & deploy gate

Retrain merges **market data** (6 tickers × 180 days) with **journal rows** when enough closed trades exist. Journal rows use **point-in-time `ml_snapshot`** stored in `risk_preview` at submit time — not current features at retrain time (avoids leakage).

A new model replaces the old one only if walk-forward AUC ≥ previous AUC − `ML_MIN_AUC_DELTA` (default 0.02). The previous model is archived to `direction_model_v{N}.joblib` before deploy.

### Journal-augmented retrain

When `ML_JOURNAL_RETRAIN_ENABLED=true` and closed trades ≥ `ML_RETRAIN_MIN_TRADES` (default 10) have snapshots + PnL:

- Features come from `approval.risk_preview.ml_snapshot` (captured at submit)
- Label: profitable buy → bullish (1); profitable sell → bearish (0)

### Model rollback

- `GET /api/intelligence/ml/history` — archived versions
- `POST /api/intelligence/ml/rollback/{version}` — restore a prior model
- **UI:** `/ml` — status, retrain, history table, rollback actions

## Env vars

See [`apps/api/.env.example`](../apps/api/.env.example) — `ML_MODEL_TYPE`, `ML_WALK_FORWARD_FOLDS`, `ML_MIN_SAMPLES`, `ML_JOURNAL_RETRAIN_ENABLED`, `ML_MAX_HISTORY_VERSIONS`, etc.

## Status API

`GET /api/intelligence/ml/status` returns version, AUC, Brier, feature importance, deploy gate status, journal trade count, history size, and a nested `volatility` object.

## Volatility / regime classifier

Separate model trained on **SPY + QQQ** macro bars. Predicts probability of **high forward 5-day volatility** (top quartile of forward daily-return std in training sample).

| Feature | Description |
|---------|-------------|
| atr_percent | ATR as % of price |
| rsi_14 | RSI(14) |
| volume_spike | Volume / 20-day avg |
| price_vs_20dma / 50dma | Trend distance |
| realized_vol_10d | 10-day return std (%) |
| vix_change | QQQ vol proxy |
| qqq_trend_numeric | Macro trend |

**Integration:**

- `RegimeService` blends rule-based regime with ML — elevates to `high_vol` when prob ≥ `ML_VOL_HIGH_THRESHOLD`
- Composite score penalized by `ml_vol_prob × ML_VOL_SCORE_PENALTY`
- Risk engine adds CAUTION when vol model is elevated

Configure via `ML_VOLATILITY_ENABLED`, `ML_VOL_HIGH_THRESHOLD`, `ML_VOL_SCORE_PENALTY`.
