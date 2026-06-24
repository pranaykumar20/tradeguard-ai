# Approval Workflow

How trades move from analysis to live execution in TradeGuard.

## Analysis is not execution

Chat and ticker analysis produce ALLOW / CAUTION / BLOCK verdicts. A verdict of ALLOW does **not** place an order. Execution requires the approval queue.

## Manual approval default

`RISK_REQUIRE_MANUAL_APPROVAL=true` by default. Every live order must be explicitly approved at `/approvals` before Robinhood MCP is called.

## Robinhood Agentic account

Connect via OAuth in `/onboarding`. TradeGuard stores encrypted per-user tokens and routes execution to the Agentic account only — never the user's primary brokerage for v1.

## Approval steps

1. User requests a trade (chat or UI).
2. Risk engine previews the trade — BLOCK stops here.
3. Approval request is created with risk and MCP previews.
4. User reviews and approves or rejects at `/approvals`.
5. On approve, `ExecutionService` calls MCP `place_order`.
6. Outcome is logged to the trade journal.

## BLOCK and CAUTION

- **BLOCK**: No approval request. Explain blocks to the user; do not suggest workarounds.
- **CAUTION**: Approval may proceed but user must acknowledge warnings first.
