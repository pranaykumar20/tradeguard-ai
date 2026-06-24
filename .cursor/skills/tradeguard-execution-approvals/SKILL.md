---
name: tradeguard-execution-approvals
description: >-
  TradeGuard execution, MCP, approval queue, and automation gates. Use when working
  on Robinhood MCP, execution service, approvals UI, monitoring halts, or automation.
---

# TradeGuard Execution & Approvals

## Execution flow

```
Chat / UI trade intent
  → RiskEngine preview (ALLOW / CAUTION / BLOCK)
  → Approval request created (if not BLOCK)
  → User approves at /approvals
  → ExecutionService → Robinhood MCP (Agentic account)
  → Journal + monitoring update
```

## Key files

| File | Role |
|------|------|
| `apps/api/app/services/execution.py` | Order preview and place via MCP |
| `apps/api/app/api/routes/approvals.py` | Approval queue API |
| `apps/web/src/app/(app)/approvals/` | Approval UI |
| `apps/api/app/services/robinhood_connect.py` | Per-user OAuth tokens |
| `apps/api/app/services/monitoring.py` | PnL alerts, trading halt |
| `apps/api/app/services/automation.py` | Kill switch, daily caps |

## Robinhood MCP

- Endpoint: `https://agent.robinhood.com/mcp/trading`
- Users connect via OAuth in `/onboarding` — no pasted API keys.
- Tokens encrypted in broker account meta (`apps/api/app/core/secrets.py`).
- Use a **separate Agentic account** — not the user's primary brokerage.

## Approval gates

- `RISK_REQUIRE_MANUAL_APPROVAL=true` by default — every live order needs explicit approve.
- Never call MCP `place_order` without a resolved approval record.
- `BLOCK` verdict → no approval request, no execution.

## Automation constraints (Phase 4)

- Master kill switch in `automation.py` — check before auto-approve paths.
- Validation gate (`validation.py`) must pass before enabling automation rules.
- Strategies (`strategies.py`) may auto-approve **ALLOW-only** trades within caps — never BLOCK.

## Monitoring halts

- Daily loss circuit breaker in `RiskEngine._daily_loss_blocks` mirrors monitoring halt.
- When halted, new trade previews should return BLOCK.

## Do not

- Execute on `BLOCK` or skip the approval queue in production paths.
- Store OAuth tokens in plaintext.
- Enable full auto-trading without validation gate + user opt-in.
- Route MCP calls before risk preview completes.
