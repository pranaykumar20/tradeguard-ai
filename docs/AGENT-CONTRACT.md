# TradeGuard Agent Contract

Human-readable spec for agent roles, boundaries, and veto rules. Cursor skills and the runtime `SYSTEM_PROMPT` must stay aligned with this document.

## Principle

**LLM explains. Code decides.** The risk engine verdict is always final.

## System flow

```
User → Next.js UI → FastAPI orchestrator
                         ↓
              Market / ML / RAG / News context
                         ↓
                   Risk Engine (veto)
                         ↓
              Structured reply + LLM narrative
                         ↓
         [optional] Approval queue → Robinhood MCP
```

## Agent roles

| Role | Location | Inputs | Outputs | Veto? |
|------|----------|--------|---------|-------|
| **Orchestrator** | `apps/api/app/agents/orchestrator.py` | User message, session | Structured reply, tool calls | No |
| **LLM narrator** | `apps/api/app/agents/llm.py` | Context + risk verdict | Short markdown narrative | No — must not contradict verdict |
| **Market** | `apps/api/app/services/features.py` | Tickers, quotes | Features (VIX, QQQ trend, etc.) | No |
| **ML** | `apps/api/app/ml/` | Features | Direction/vol scores | No — advisory warnings only |
| **RAG** | `apps/api/app/rag/` | Query | Playbook/filing/news chunks | No |
| **Risk** | `apps/api/app/risk/engine.py` | Features, portfolio, side | ALLOW / CAUTION / BLOCK | **Yes** |
| **Execution** | `apps/api/app/services/execution.py` | Approved request | MCP preview/place | Blocked if risk says BLOCK |
| **Journal** | journal services + UI | Trade outcomes | Paper/live log | No |
| **Monitoring** | `apps/api/app/services/monitoring.py` | PnL, limits | Alerts, auto-halt | Can halt new trades |

## Verdict contract

| Verdict | User-facing meaning | Execution |
|---------|---------------------|-----------|
| `ALLOW` | Passes hard rules | May enter approval queue |
| `CAUTION` | Warnings present | Manual review required |
| `BLOCK` | Hard rule violated | No order, no MCP place |

## Execution contract

1. User connects Robinhood Agentic account via OAuth (`/onboarding`).
2. Trade intent flows through risk preview.
3. User submits to **approval queue** (`/approvals`).
4. On approve, `ExecutionService` calls Robinhood MCP.
5. `RISK_REQUIRE_MANUAL_APPROVAL=true` by default — never skip unless explicitly changing product policy.

## RAG contract

- Playbooks in `docs/playbooks/*.md` are indexed at startup (`apps/api/app/rag/indexer.py`).
- LLM cites playbooks with `[1]` markers; content must match `RiskRules` defaults.
- Policy changes require the sync workflow in `docs/POLICY-SYNC.md`.

## Disclaimer boundary

TradeGuard provides **analysis and risk tooling**, not personalized financial advice. All user-facing agents must avoid guaranteeing returns or implying orders were placed without approval confirmation.

## Related docs

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system diagram
- [POLICY-SYNC.md](./POLICY-SYNC.md) — how to keep code, playbooks, and prompts aligned
- [MCP-SETUP.md](./MCP-SETUP.md) — Robinhood OAuth setup
- [PLAN.md](./PLAN.md) — phased product roadmap
