---
name: tradeguard-ai-orchestration
description: >-
  TradeGuard chat orchestration — intent routing, RAG tools, structured responses,
  streaming. Use when editing orchestrator, chat routes, intent detection, or response builders.
---

# TradeGuard AI Orchestration

## Flow

```
POST /api/chat or /api/chat/stream
  → detect_intent (apps/api/app/agents/intent.py)
  → RAG tool routing (apps/api/app/rag/router.py, tool_routing.py)
  → Feature / quote / news fetch
  → RiskEngine.evaluate_*
  → build structured response (response_builder.py)
  → LLM narrative (llm.py) — optional streaming
  → validate_grounded_reply (llm_validator.py)
```

## Key files

| File | Role |
|------|------|
| `apps/api/app/agents/orchestrator.py` | Main `TradeGuardOrchestrator` |
| `apps/api/app/agents/intent.py` | Intent classification |
| `apps/api/app/agents/response_builder.py` | Structured UI payloads |
| `apps/api/app/rag/tools.py` | `search_playbooks`, filings, journal tools |
| `apps/api/app/api/routes/chat.py` | HTTP endpoints |

## RAG tool routing

- `infer_rag_tools()` in `tool_routing.py` picks tools from message keywords.
- Default fallback includes `search_playbooks`.
- Golden eval queries: `apps/api/app/rag/eval/golden_queries.json`.

## Structured vs narrative

- UI renders scores, verdicts, tables from structured fields.
- LLM `SYSTEM_PROMPT` adds short narrative only — see `agents-llm` rule.

## Trade intent

- Ticker + side patterns in orchestrator trigger risk preview.
- Option mentions respect `RISK_ALLOW_OPTIONS`.

## Do not

- Return execution confirmation without approval queue state.
- Bypass risk engine for trade-intent messages.
- Break streaming path when changing `generate_reply` / `stream_reply`.
