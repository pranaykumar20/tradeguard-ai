# Architecture

## System diagram

```mermaid
flowchart TB
    User[User] --> Web[Next.js Dashboard]
    Web --> API[FastAPI API]
    API --> LLM[LLM Provider]
    API --> RAG[RAG / pgvector]
    API --> ML[ML Scoring Engine]
    API --> Risk[Risk Engine]
    Risk -->|veto| MCP[Robinhood MCP]
    API --> PG[(PostgreSQL)]
    API --> Redis[(Redis)]
    Celery[Celery Workers] --> ML
    Celery --> Redis
```

## Agent roles

| Agent | Responsibility |
|-------|----------------|
| **Orchestrator** | Parses intent, routes to services, formats response |
| **Market** | SPY, QQQ, VIX, sector ETFs (Phase 2) |
| **Stock** | Per-ticker features and scores |
| **News** | Sentiment from headlines (Phase 2) |
| **ML** | Direction/volatility models |
| **Risk** | Hard rules — **veto power** |
| **Portfolio** | Exposure, correlation, concentration |
| **Execution** | MCP order preview/place (Phase 3) |
| **Journal** | Trade log and outcomes (Phase 2) |

## Phase 1 (current)

- Demo portfolio + deterministic feature scoring
- Keyword RAG over risk playbooks
- Risk engine with CAUTION / BLOCK / ALLOW
- Chat API without live MCP execution

## Phase 2

- Live market data (Polygon/FRED)
- pgvector RAG ingestion
- Celery async feature refresh
- Paper trade journal

## Phase 3

- Robinhood MCP live connection
- Order preview + manual approval UI
- Small Agentic account execution
