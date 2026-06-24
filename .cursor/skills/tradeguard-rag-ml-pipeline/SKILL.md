---
name: tradeguard-rag-ml-pipeline
description: >-
  TradeGuard RAG indexing, playbooks, embeddings, and ML scoring/retrain. Use when
  editing RAG indexer, playbooks, embeddings, ML models, or feature scoring.
---

# TradeGuard RAG & ML Pipeline

## RAG

| Component | Path |
|-----------|------|
| Playbook loader | `apps/api/app/rag/playbooks.py` |
| Indexer | `apps/api/app/rag/indexer.py` |
| Vector store | pgvector via `apps/api/app/db/storage.py` |
| Retrieval | `apps/api/app/rag/retrieval.py`, `service.py` |
| Chunkers | `apps/api/app/rag/chunkers/` |

Playbooks in `docs/playbooks/*.md` are indexed on API startup. Override dir with `RAG_PLAYBOOKS_DIR`.

### Embedding providers

- Mock when no `OPENAI_API_KEY` (`embedding_provider=mock`).
- Live OpenAI embeddings when key set.
- Config: `EMBEDDING_PROVIDER`, `OPENAI_API_KEY`.

## ML

| Component | Path |
|-----------|------|
| Direction model | `apps/api/app/ml/` |
| Scoring | `apps/api/app/ml/scoring.py` |
| Bootstrap | `apps/api/app/services/ml_bootstrap.py` |
| Retrain | `apps/api/app/services/ml_retrain.py` |
| Volatility | `apps/api/app/ml/volatility_registry.py` |

### Risk integration

- ML bullish probability → `_ml_hybrid_warnings` in `RiskEngine` (warnings only).
- Volatility model → `_volatility_ml_warnings` when `ML_VOLATILITY_ENABLED=true`.
- Thresholds: `ML_BULLISH_BUY_MIN`, `ML_BULLISH_SELL_MAX`, `ML_VOL_HIGH_THRESHOLD`.

### Journal-augmented retrain

- `ML_JOURNAL_RETRAIN_ENABLED` — uses trade journal outcomes.
- Admin API: `/api/intelligence/ml`.

## After changes

1. Playbook edits → restart API or trigger reindex.
2. Model changes → run tests in `apps/api/tests/`.
3. New doc types → update `apps/api/app/rag/schemas.py` and chunker.

## Do not

- Index playbook text that contradicts `RiskRules`.
- Treat ML score as a hard block without code in `RiskEngine`.
- Require live embedding keys in unit tests.
