# Automation Gates

Rules before TradeGuard may auto-approve trades or run strategy rules without per-trade review.

## Manual approval baseline

`RISK_REQUIRE_MANUAL_APPROVAL=true` is the production default. Automation features are additive constraints, not a bypass.

## Validation gate

`apps/api/app/services/validation.py` builds a track-record report (Sharpe, drawdown, win rate). Automation and semi-auto strategies remain blocked until the validation gate passes. Config: `VALIDATION_GATE_ENABLED`.

## Master kill switch

`apps/api/app/services/automation.py` exposes a global enable/disable. When disabled, no strategy may auto-approve regardless of ALLOW verdict.

## Strategy auto-approve limits

- Only **ALLOW** verdicts may be auto-approved — never CAUTION or BLOCK.
- Daily caps and per-strategy limits apply in `apps/api/app/services/strategies.py`.
- ALLOW-only auto-approve is Phase 4 constrained automation — not full autonomous trading.

## Recommended track record

Require 3+ months of validated paper or small live results before enabling automation rules. Document the decision in the journal.

## Monitoring integration

If monitoring halts trading (daily loss circuit breaker via `RISK_MAX_DAILY_LOSS_USD`), automation must not place new orders until the halt clears.
