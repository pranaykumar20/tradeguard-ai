# Robinhood Agentic Trading MCP Setup

TradeGuard connects to Robinhood through the **Model Context Protocol (MCP)**. Each user links their own **Agentic account** via OAuth in the onboarding wizard (`/onboarding`).

## Prerequisites

- Robinhood account with Agentic Trading enabled
- Desktop browser (Robinhood Agentic account setup requires desktop)
- TradeGuard API reachable at a public URL for OAuth callback (`API_PUBLIC_URL`)

## In-app connection (recommended)

1. Sign in to TradeGuard and open **Account setup** (`/onboarding`).
2. Click **Connect Robinhood** — you are redirected to Robinhood OAuth.
3. Complete Robinhood Agentic account onboarding if prompted.
4. Fund your separate Agentic account ($500–$1,000 recommended).
5. Return to TradeGuard — the connect step completes automatically.

OAuth tokens are stored **encrypted per user** in your broker account record. TradeGuard never asks you to paste an MCP URL.

## Operator / legacy env config (optional)

For single-tenant deployments you can still set a global MCP URL:

```bash
# apps/api/.env
ROBINHOOD_MCP_URL=https://agent.robinhood.com/mcp/trading
ROBINHOOD_MCP_ENABLED=true
API_PUBLIC_URL=https://your-api.example.com
FRONTEND_URL=https://your-app.example.com
SECRETS_ENCRYPTION_KEY=   # Fernet key; generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep manual approval on:

```bash
RISK_REQUIRE_MANUAL_APPROVAL=true
RISK_ALLOW_OPTIONS=false
RISK_MAX_TRADE_USD=250
```

## Robinhood MCP endpoint

All users connect to the same MCP server URL; authentication is per-user via OAuth:

`https://agent.robinhood.com/mcp/trading`

## Safety

- TradeGuard's risk engine runs **before** any MCP order call
- `place_order` requires explicit user approval
- Never disable `RISK_REQUIRE_MANUAL_APPROVAL` until you have 3+ months of validated results

## References

- [Robinhood Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)
- [Trading with your agent](https://robinhood.com/us/en/support/articles/trading-with-your-agent/)
- [MCP specification](https://modelcontextprotocol.io/)
