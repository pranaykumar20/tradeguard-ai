# Robinhood Agentic Trading MCP Setup

TradeGuard connects to Robinhood through the **Model Context Protocol (MCP)**. The agent reads portfolio data and places trades only in your separate **Agentic account**.

## Prerequisites

- Robinhood account with Agentic Trading enabled
- Desktop browser (setup cannot be done on mobile only)
- ChatGPT or another MCP-capable AI platform for initial Robinhood connection testing

## Steps

1. **Enable Agentic Trading** in Robinhood (Settings → Agentic Trading).
2. **Fund a separate Agentic account** — start with $500–$1,000, not your main portfolio.
3. **Connect MCP** from Robinhood's agent setup page and copy the MCP server URL.
4. **Configure TradeGuard**:

```bash
# apps/api/.env
ROBINHOOD_MCP_URL=https://...
ROBINHOOD_MCP_ENABLED=true
```

5. **Keep manual approval on**:

```bash
RISK_REQUIRE_MANUAL_APPROVAL=true
RISK_ALLOW_OPTIONS=false
RISK_MAX_TRADE_USD=250
```

## Available MCP tools (Robinhood)

- Portfolio snapshot, buying power, positions
- Ticker search, equity quotes, watchlists
- Order review, placement, cancellation
- Options tools (rolling out — keep disabled in TradeGuard v1)

## Safety

- TradeGuard's risk engine runs **before** any MCP order call
- `place_order` requires explicit user approval in Phase 3+
- Never disable `RISK_REQUIRE_MANUAL_APPROVAL` until you have 3+ months of validated results

## References

- [Robinhood Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)
- [Trading with your agent](https://robinhood.com/us/en/support/articles/trading-with-your-agent/)
- [MCP specification](https://modelcontextprotocol.io/)
