---
name: tradeguard-trading-playbooks
description: >-
  Map TradeGuard playbooks to risk rules and RAG. Use when editing docs/playbooks/,
  RAG content, chat policy answers, or aligning user-facing text with code limits.
---

# TradeGuard Trading Playbooks

## Indexing

Playbooks live in `docs/playbooks/*.md`. Loaded by `apps/api/app/rag/playbooks.py` and indexed via `RAGIndexer.index_playbooks()` on API startup.

## Playbook → code mapping

| Playbook | Code / config |
|----------|---------------|
| `risk-playbook.md` | QQQ/VIX regime, limit orders, no-trade window, daily loss |
| `position-sizing.md` | `RISK_MAX_TRADE_USD`, scale-in guidance |
| `sector-rules.md` | `RISK_MAX_TECH_SECTOR_PCT`, tech concentration warnings |
| `options-policy.md` | `RISK_ALLOW_OPTIONS`, manual approval |
| `tax-rules.md` | `WASH_SALE_WINDOW_DAYS`, tax lot tracking |
| `regime-and-vix.md` | `regime.py`, `ML_VOL_*` settings |
| `approval-workflow.md` | `RISK_REQUIRE_MANUAL_APPROVAL`, `/approvals` |
| `automation-gates.md` | validation gate, automation kill switch |

## Writing playbook sections

Each section should:

1. State the rule in plain language a trader would understand.
2. Reference the config key where applicable (e.g. `RISK_MAX_DAILY_LOSS_USD`).
3. Match the numeric defaults in `apps/api/app/risk/rules.py` — do not contradict code.

## Format

Use `##` headings per topic. The chunker in `apps/api/app/rag/chunkers/playbook.py` splits on headings for RAG retrieval.

## After editing playbooks

1. Restart API or trigger RAG reindex so pgvector picks up changes.
2. Run golden eval if routing changed: `apps/api/app/rag/eval/golden_queries.json`.
3. Update `SYSTEM_PROMPT` in `llm.py` only if user-facing tone must change.

## Do not

- Add playbook text that contradicts `RiskEngine` blocks.
- Promise auto-execution in playbook copy when `RISK_REQUIRE_MANUAL_APPROVAL=true`.
- Remove config key references — they help devs and RAG stay aligned.
