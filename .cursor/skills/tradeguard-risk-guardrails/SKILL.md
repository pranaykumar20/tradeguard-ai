---
name: tradeguard-risk-guardrails
description: >-
  TradeGuard risk engine guardrails — ALLOW/CAUTION/BLOCK semantics, circuit breakers,
  sector limits, ML advisory warnings. Use when adding risk rules, trade preview,
  approvals, strategies, or any code that affects trade decisions.
---

# TradeGuard Risk Guardrails

## Source of truth

| File | Role |
|------|------|
| `apps/api/app/risk/rules.py` | `RiskRules` model + env-backed defaults |
| `apps/api/app/risk/engine.py` | `RiskEngine.evaluate_*` — enforcement |
| `apps/api/app/core/config.py` | `RISK_*` env vars |
| `docs/playbooks/*.md` | RAG-indexed policy text (must stay aligned) |

See also `docs/AGENT-CONTRACT.md`.

## Verdict semantics

| Verdict | Meaning | Dev behavior |
|---------|---------|--------------|
| **ALLOW** | Passes all hard rules | May proceed to approval queue if execution requested |
| **CAUTION** | Warnings only | User must review; never auto-execute |
| **BLOCK** | Hard rule violated | Stop — no MCP call, no softening in LLM layer |

`BLOCK` reasons live in `RiskVerdict.blocks`. `CAUTION` reasons live in `warnings`. ML hybrid signals are **warnings only**, never blocks.

## Default limits (config keys)

| Rule | Default | Config |
|------|---------|--------|
| Max trade size | $250 | `RISK_MAX_TRADE_USD` |
| Daily loss circuit breaker | $50 | `RISK_MAX_DAILY_LOSS_USD` |
| Single-name concentration | 20% | `RISK_MAX_SINGLE_NAME_PCT` |
| Tech sector cap | 30% | `RISK_MAX_TECH_SECTOR_PCT` |
| Manual approval required | true | `RISK_REQUIRE_MANUAL_APPROVAL` |
| Options allowed | false | `RISK_ALLOW_OPTIONS` |
| No-trade window after open | 10 min | `no_trade_first_minutes` in `RiskRules` |
| Allowed tickers | NVDA, MSFT, META, TSLA, QQQ, GBTC | `allowed_tickers` in `RiskRules` |

## Trading operator knowledge

- **Regime**: Rising VIX + weak QQQ trend → reduce size; see `regime-and-vix.md` playbook.
- **Hidden correlation**: NVDA + META + MSFT + QQQ stack tech exposure — sector cap matters.
- **Circuit breaker**: When daily P&L hits `-max_daily_loss_usd`, all new trades block until review.
- **Order types**: Market orders blocked on volatile names when `allow_market_orders` is false.

## How to add a new rule

1. Add field to `RiskRules` if needed; wire `default_rules()` to `settings`.
2. Enforce in `RiskEngine` — return `blocks` for hard stops, `warnings` for soft signals.
3. Add unit test in `apps/api/tests/`.
4. Add matching section in `docs/playbooks/` (see `tradeguard-trading-playbooks` skill).
5. Update `docs/POLICY-SYNC.md` checklist if user-facing language changes.

## Do not

- Move risk checks after the LLM or orchestrator narrative step.
- Convert a `BLOCK` into `CAUTION` in prompts or UI copy.
- Auto-execute trades that received `BLOCK` or skipped manual approval.
- Treat ML probability as a substitute for hard rules.
- Add prompt-only guardrails without code enforcement.
