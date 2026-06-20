# TradeGuard AI — Complete Phased Build Plan

> Living roadmap for TradeGuard AI. Update status as sub-phases ship.

## Vision

TradeGuard AI is **not an auto-trader**. It is an AI risk manager that orchestrates analysis, applies hard-coded guardrails with veto power, and only later connects to Robinhood MCP for guarded execution.

```mermaid
flowchart TB
    subgraph phase1 [Phase1 AnalysisOnly]
        User1[User] --> Web1[Next.js Dashboard]
        Web1 --> API1[FastAPI]
        API1 --> LLM1[LLM Orchestrator]
        API1 --> ML1[ML Scoring]
        API1 --> RAG1[RAG]
        API1 --> Risk1[Risk Engine Veto]
    end

    subgraph phase2 [Phase2 PaperTrading]
        API1 --> PG[(PostgreSQL pgvector)]
        API1 --> Redis[(Redis Celery)]
        API1 --> Market[Live Market Data]
        API1 --> Journal[Trade Journal]
    end

    subgraph phase3 [Phase3 LiveExecution]
        Risk1 -->|approved| MCP[Robinhood MCP]
        MCP --> Agentic[Agentic Account]
    end

    subgraph phase4 [Phase4 Automation]
        Monitor[Monitoring Alerts] --> Auto[Semi Automation]
        Auto -->|3mo track record| LimitedAuto[Limited Auto Rules]
    end

    phase1 --> phase2 --> phase3 --> phase4
```

---

## Implementation Status (June 2026)

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 1** — Analysis only | **Done** | Risk engine, LLM orchestrator, dashboard, RAG, ticker analysis |
| **Phase 2** — Paper trading | **Done** | Mock-first providers, journal, pgvector RAG, advanced risk dashboard |
| **Phase 3** — Guarded execution | **Done** | MCP layer, execution flow, approvals UI at `/approvals` |
| **Phase 4.1** — Monitoring & alerts | **Done** | PnL monitoring, auto-halt, Slack alerts (mock-first) |
| **Phase 4.2** — Semi-auto strategies | **Done** | Pre-defined rules, ALLOW-only auto-approve, `/strategies` UI |
| **Phase 4.3** — Validation gate | **Done** | Sharpe, drawdown, win rate report; blocks automation until pass |
| **Phase 4.4** — Constrained automation | **Done** | Master kill switch, daily caps, ALLOW-only, audit trail |

**Provider pattern:** All external services use `auto` mode — mock when no API key, live when configured. Swap keys at the end; no code changes required.

| Service | Mock (default) | Live (add key) | Env var |
|---------|----------------|----------------|---------|
| Market data | `MockMarketDataProvider` | Polygon | `POLYGON_API_KEY` |
| Embeddings / RAG | `MockEmbeddingProvider` | OpenAI | `OPENAI_API_KEY` |
| MCP / execution | `MockRobinhoodMCPClient` | Live MCP SDK | `ROBINHOOD_MCP_URL` |
| Alerts | `MockAlertProvider` | Slack webhook | `SLACK_WEBHOOK_URL` |
| Storage | File-backed memory | PostgreSQL + pgvector | `docker compose up -d` |

---

## Phase 1 — Analysis Only (no execution)

**Goal:** User can chat with TradeGuard, see portfolio risk, sector exposure, ticker analysis, and CAUTION/BLOCK verdicts — all on demo data. No orders placed.

| Sub-phase | Description | Status |
|-----------|-------------|--------|
| **1.1** Dev foundation | CORS, env templates, health indicator, Docker Compose | Done |
| **1.2** Risk engine | Enforce all rules, real features in preview, unit tests | Done |
| **1.3** LLM orchestrator | OpenAI/Anthropic, tool routing, trade intent parsing | Done |
| **1.4** Frontend | Portfolio, dashboard, sidebar, chat wiring | Done |
| **1.5** RAG + analysis | Expanded playbooks, ticker analysis UI | Done |

**Gate:** End-to-end demo without MCP or live market data. ✅

---

## Phase 2 — Paper Trading and Live Intelligence

**Goal:** Replace demo data with real market feeds, persist state, build a 100-trade paper journal, and upgrade RAG to vector search.

| Sub-phase | Description | Status |
|-----------|-------------|--------|
| **2.1** Database & persistence | SQLAlchemy models, pgvector, storage abstraction | Done |
| **2.2** Live market data | Polygon provider + mock fallback, Celery refresh | Done |
| **2.3** ML training | Direction model bootstrap, scoring pipeline | Done |
| **2.4** Vector RAG | Mock/live embeddings, pgvector search | Done |
| **2.5** Paper trade journal | Journal API + UI at `/journal` | Done |
| **2.6** Advanced risk dashboard | VaR, correlation, stress tests | Done |

**Gate:** 100 paper trades logged; live data flowing when keys set. ✅ (mock mode works without keys)

---

## Phase 3 — Small Agentic Account (manual approval)

**Goal:** Connect Robinhood MCP, read live Agentic account portfolio, preview orders, and execute only after explicit user approval.

| Sub-phase | Description | Status |
|-----------|-------------|--------|
| **3.1** MCP client | Mock + live clients, portfolio/quotes | Done |
| **3.2** Order preview | Risk gate → MCP preview, execution API | Done |
| **3.3** Manual approval UI | `/approvals` queue, approve/reject | Done |
| **3.4** Guarded execution | place_order with approval, journal auto-log | Done |

**Gate (before live Phase 4):**
- Separate Agentic account funded ($500–$1,000)
- 3+ months of live manual-approved trades with documented results
- Zero options automation; daily loss circuit breaker tested

---

## Phase 4 — Limited Automation (post-validation)

**Goal:** After proven track record, allow selective automation — still no options, still risk-engine veto, still small position sizes.

### Phase 4.1 — Monitoring and alerting *(done)*

- Real-time PnL monitoring, daily loss circuit breaker (auto-halt trading)
- Slack/email alerts on BLOCK events, large drawdowns, MCP failures
- Monitoring dashboard at `/monitoring`
- **Exit criteria:** Trading halts automatically when daily loss limit hit ✅

### Phase 4.2 — Semi-automated trade plans *(done)*

- User defines approved strategies (e.g. "rebalance QQQ if tech exposure > 25%")
- Agent proposes trades; risk engine evaluates; user can opt into auto-approve for pre-defined rules only
- Strategies UI at `/strategies`
- **Exit criteria:** One strategy runs with auto-approve for ALLOW-only rebalancing ✅

### Phase 4.3 — Performance validation gate *(done)*

- Require 3+ months positive risk-adjusted returns from Phase 3 journal
- Automated report: Sharpe, max drawdown, win rate, rule violation count
- Validation UI at `/validation`
- **Exit criteria:** Gate blocks Phase 4.4 until metrics pass configured thresholds ✅

### Phase 4.4 — Constrained automation *(done)*

- Auto-execute only ALLOW verdicts within pre-approved strategy bounds
- Hard caps remain: no options, max position size, sector limits, manual override always available
- Master kill switch at `/automation` — disable instantly
- Full audit trail in automation log + journal
- **Exit criteria:** Automation can be disabled instantly; full audit trail in journal ✅

---

## Build Sequence

```mermaid
gantt
    title TradeGuard Build Sequence
    dateFormat YYYY-MM
    section Phase1
    1.1 DevFoundation     :done, p11, 2026-06, 1w
    1.2 RiskEngine        :done, p12, after p11, 1w
    1.3 LLMOrchestrator   :done, p13, after p12, 2w
    1.4 Frontend          :done, p14, after p13, 2w
    1.5 RAGPolish         :done, p15, after p14, 1w
    section Phase2
    2.1 Database          :done, p21, after p15, 2w
    2.2 MarketData        :done, p22, after p21, 2w
    2.3 MLTraining        :done, p23, after p22, 2w
    2.4 VectorRAG         :done, p24, after p23, 2w
    2.5 PaperJournal      :done, p25, after p24, 3w
    2.6 AdvDashboard      :done, p26, after p25, 2w
    section Phase3
    3.1 MCPConnect        :done, p31, after p26, 2w
    3.2 OrderPreview      :done, p32, after p31, 2w
    3.3 ApprovalsUI       :done, p33, after p32, 2w
    3.4 Execution         :done, p34, after p33, 2w
    section Phase4
    4.1 Monitoring        :done, p41, after p34, 2w
    4.2 SemiAuto          :done, p42, after p41, 3w
    4.3 ValidationGate    :done, p43, after p42, 4w
    4.4 Automation        :done, p44, after p43, 3w
```

**Phase 4 complete.** All four phases implemented (mock-first; swap API keys for live).

---

## Default Risk Guardrails (all phases)

Configured in `apps/api/app/risk/rules.py` — never weaken without explicit gate approval:

- Max single-name exposure: 20%
- Max tech sector exposure: 30%
- Max trade size: $250
- Max daily loss: $50
- Allowed tickers: NVDA, MSFT, META, TSLA, QQQ, GBTC
- No options without manual approval
- Limit orders only for volatile tickers

---

## Key Files

| Area | Path |
|------|------|
| Architecture | [docs/ARCHITECTURE.md](./ARCHITECTURE.md) |
| MCP setup | [docs/MCP-SETUP.md](./MCP-SETUP.md) |
| Risk engine | `apps/api/app/risk/engine.py` |
| Execution | `apps/api/app/services/execution.py` |
| Monitoring | `apps/api/app/services/monitoring.py` |
| Strategies | `apps/api/app/services/strategies.py` |
| Validation | `apps/api/app/services/validation.py` |
| Automation | `apps/api/app/services/automation.py` |
| Web dashboard | `apps/web/src/app/` |
