# Regime and VIX

Market regime rules for position sizing and new entries.

## VIX elevation

When VIX is rising sharply (`vix_change` elevated in features), treat the environment as high volatility. Reduce new position size and prefer limit orders. Config: ML vol warnings use `ML_VOL_HIGH_THRESHOLD` and `ML_VOL_SCORE_PENALTY`.

## QQQ trend filter

Do not add to a tech-heavy portfolio when QQQ is below its 50-day moving average and VIX is rising. The risk engine surfaces CAUTION warnings in this regime via feature checks in `apps/api/app/risk/engine.py`.

## Regime detection

`apps/api/app/services/regime.py` classifies macro regime (risk-on / risk-off). Regime-adjusted scores feed the orchestrator — they inform narrative, not veto. Hard blocks still come from `RiskEngine`.

## ML volatility overlay

When `ML_VOLATILITY_ENABLED=true` and `ml_vol_prob` exceeds `ML_VOL_HIGH_THRESHOLD`, expect wider swings — scale down size per `position-sizing.md`.
