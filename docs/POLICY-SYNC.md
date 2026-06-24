# Policy Sync Checklist

Keep **code**, **playbooks**, **runtime prompt**, and **Cursor skills** aligned when trading or risk behavior changes.

## Principle

**LLM explains. Code decides.** `apps/api/app/risk/engine.py` is the enforcement layer. Playbooks and prompts describe the same rules — they do not replace them.

## Checklist

When adding or changing a trading rule:

- [ ] **Code** — `apps/api/app/risk/rules.py` + `apps/api/app/risk/engine.py`
- [ ] **Config** — `apps/api/app/core/config.py` + `apps/api/.env.example`
- [ ] **Tests** — `apps/api/tests/` (risk, connect, or feature tests as appropriate)
- [ ] **Playbook** — matching section in `docs/playbooks/*.md` with config key cited
- [ ] **Runtime prompt** — `SYSTEM_PROMPT` in `apps/api/app/agents/llm.py` if user-facing language changes
- [ ] **Cursor** — `tradeguard-risk-guardrails` skill + `risk-engine-changes` rule if semantics change
- [ ] **RAG** — restart API or reindex playbooks (automatic on startup via `RAGIndexer`)
- [ ] **Deploy docs** — `docs/RAILWAY.md` if new production env vars

## Layer map

| Layer | Location | Audience |
|-------|----------|----------|
| Enforcement | `risk/rules.py`, `risk/engine.py` | Runtime |
| User RAG | `docs/playbooks/*.md` | End users (chat) |
| Narrator | `agents/llm.py` `SYSTEM_PROMPT` | End users (chat) |
| Dev agent | `.cursor/skills/`, `.cursor/rules/` | Engineers |
| Spec | `docs/AGENT-CONTRACT.md` | Everyone |

## Playbook → config quick reference

| Playbook | Primary config |
|----------|----------------|
| `position-sizing.md` | `RISK_MAX_TRADE_USD` |
| `sector-rules.md` | `RISK_MAX_TECH_SECTOR_PCT` |
| `options-policy.md` | `RISK_ALLOW_OPTIONS` |
| `risk-playbook.md` | `RISK_MAX_DAILY_LOSS_USD`, no-trade window |
| `tax-rules.md` | `WASH_SALE_WINDOW_DAYS` |
| `regime-and-vix.md` | `ML_VOL_*`, regime service |
| `approval-workflow.md` | `RISK_REQUIRE_MANUAL_APPROVAL` |
| `automation-gates.md` | `VALIDATION_GATE_ENABLED`, automation kill switch |

## Related

- [AGENT-CONTRACT.md](./AGENT-CONTRACT.md) — agent roles and veto boundaries
- [ARCHITECTURE.md](./ARCHITECTURE.md) — system diagram
