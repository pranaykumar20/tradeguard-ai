# TradeGuard AI

**AI Stock Risk Manager** — not an auto-trader. TradeGuard combines LLM orchestration, ML signal engines, RAG over financial knowledge, a code-based risk engine with veto power, and Robinhood Agentic Trading MCP for guarded execution.

```
User instruction
   ↓
LLM Agent (explain + orchestrate)
   ↓
Market Data + Feature Engineering
   ↓
ML Signal Models
   ↓
Risk Engine (hard rules — veto power)
   ↓
Trade Decision Engine
   ↓
Robinhood MCP (Agentic account only)
   ↓
Monitoring + Journal
```

## Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 16, TypeScript, Tailwind CSS | Dashboard, Ask AI chat, risk panels, trade preview |
| **Backend API** | FastAPI, Python 3.12, Pydantic v2 | Orchestration, risk engine, ML pipeline, MCP client |
| **Database** | PostgreSQL 16 + pgvector | Users, portfolios, trade journal, vector RAG |
| **Cache / Queue** | Redis 7, Celery | Session cache, async ML jobs, market data refresh |
| **ML** | scikit-learn, XGBoost, pandas, ta | Direction/volatility signals, feature engineering |
| **RAG** | pgvector + OpenAI/Voyage embeddings | SEC filings, strategy docs, risk playbooks |
| **LLM** | OpenAI / Anthropic via AI SDK | Chat brain — explains, never final trader |
| **MCP** | Model Context Protocol (Robinhood Trading MCP) | Portfolio read, quotes, order preview/place |
| **Infra** | Docker Compose (local), Vercel + Railway/Fly (prod) | Dev parity, deploy |

## Monorepo layout

```
tradeguard-ai/
├── apps/
│   ├── web/          # Next.js dashboard (Ask AI, risk snapshot, approvals)
│   └── api/          # FastAPI — risk engine, ML, RAG, MCP orchestration
├── docs/             # Architecture, phase plans, MCP setup
├── docker-compose.yml
└── package.json      # Root scripts (dev both apps)
```

## Phase roadmap

See **[docs/PLAN.md](docs/PLAN.md)** for the full living roadmap with sub-phase status.

1. **Phase 1 — Analysis only**: portfolio risk, sector exposure, CAUTION/BLOCK decisions, no execution — **Done**
2. **Phase 2 — Paper trading**: trade plans, journal, 100-trade track record — **Done**
3. **Phase 3 — Small Agentic account**: manual approval, stocks/ETFs only, max position rules — **Done**
4. **Phase 4 — Automation**: monitoring, strategies, validation gate, constrained automation — **Done**
5. **Phase 5 — Production**: API deploy, auth, email alerts, CI/CD — **In progress** (see [docs/DEPLOY.md](docs/DEPLOY.md))
6. **Phases 6–9**: intelligence, execution expansion, observability, product UX — **Planned**

## Quick start

### 1. Infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL (pgvector) on `localhost:5433` and Redis on `localhost:6380`.

### 2. Backend API

```bash
cd apps/api
python3.12 -m venv .venv    # requires Python 3.12 (3.14 is not supported yet)
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip && pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```bash
npm install
cp apps/web/.env.example apps/web/.env.local
npm run dev:web
```

Open http://localhost:3000

### 4. Run both (from repo root)

```bash
npm install
npm run dev
```

## Default risk rules (Phase 1)

Configured in `apps/api/app/risk/rules.py`:

- Max single-name exposure: 20%
- Max tech sector exposure: 30%
- Max trade size: $250
- Max daily loss: $50
- No options without manual approval
- Limit orders only for volatile tickers
- Allowed tickers: NVDA, MSFT, META, TSLA, QQQ, GBTC

## Robinhood MCP setup

See [docs/MCP-SETUP.md](docs/MCP-SETUP.md). Connect from a **desktop browser** only. Fund a separate **Agentic account** — never your main portfolio for v1.

## Disclaimer

TradeGuard AI provides analysis and risk tooling, **not financial advice**. Agentic trading can lose your entire investment. AI agents can misread instructions. Always use manual approval and small capital when starting.

## License

MIT
