"""Intelligence API — news, filings, regime, ML retrain (Phase 6)."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services.ml_retrain import MLRetrainService
from app.services.news import NewsService
from app.services.regime import RegimeService
from app.services.sec_filings import SecFilingService
from app.rag.indexer import RAGIndexer

router = APIRouter()
news = NewsService()
filings = SecFilingService()
regime = RegimeService()
ml = MLRetrainService()


@router.get("/news/{ticker}")
async def ticker_news(ticker: str, limit: int = 8):
    return await news.get_ticker_news(ticker, limit=limit)


@router.get("/market-news")
async def market_news(limit: int = 8):
    """Real-time broad market headlines via Tavily web search."""
    return await news.get_market_pulse(limit=limit)


@router.get("/filings/{ticker}")
async def ticker_filings(ticker: str):
    return await filings.get_filings(ticker)


@router.get("/filings/search")
async def search_filings(q: str, top_k: int = 3):
    results = await filings.search_filings(q, top_k=top_k)
    return {"query": q, "results": results}


@router.get("/regime")
async def macro_regime():
    return await regime.detect()


@router.get("/ml/status")
async def ml_status():
    return await ml.status()


@router.post("/ml/retrain")
async def ml_retrain():
    result = await ml.retrain()
    if result.get("status") == "skipped":
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/ml/history")
async def ml_history():
    return await ml.history()


@router.post("/ml/rollback/{version}")
async def ml_rollback(version: int):
    result = await ml.rollback(version)
    if result.get("status") != "ok":
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/rag/refresh")
async def refresh_rag_index():
    """Re-index playbooks, SEC filings, news, and journal into pgvector."""
    return await RAGIndexer().refresh_all()


@router.post("/rag/refresh/{source}")
async def refresh_rag_source(source: str):
    """Re-index a single RAG source: playbooks, filings, news, journal, or all."""
    if not settings.rag_partial_refresh_enabled:
        raise HTTPException(status_code=403, detail="Partial RAG refresh is disabled")
    from app.rag.schemas import RAG_SOURCES

    if source not in RAG_SOURCES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown source '{source}'. Valid: {', '.join(sorted(RAG_SOURCES))}",
        )
    try:
        return await RAGIndexer().refresh_source(source)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/rag/journal/reindex")
async def reindex_journal_rag():
    """Re-index closed trades for the current user."""
    from app.rag.journal_index import index_user_journal

    return {"indexed": await index_user_journal()}


@router.get("/rag/status")
async def rag_status():
    """RAG corpus and pipeline status."""
    from app.db.storage import get_storage
    from app.rag.eval.runner import get_last_eval_report

    storage = await get_storage()
    docs = await storage.list_rag_documents_raw()
    by_type: dict[str, int] = {}
    for doc in docs:
        doc_type = (doc.get("meta") or {}).get("type", "document")
        by_type[doc_type] = by_type.get(doc_type, 0) + 1

    last_eval = await get_last_eval_report()
    return {
        "documents_total": len(docs),
        "documents_by_type": by_type,
        "embedding_version": settings.rag_embedding_version,
        "router_enabled": settings.rag_router_enabled,
        "eval_enabled": settings.rag_eval_enabled,
        "last_eval": last_eval,
    }


@router.get("/rag/eval")
async def rag_eval_report():
    from app.rag.eval.runner import get_last_eval_report

    report = await get_last_eval_report()
    if not report:
        return {"status": "no_report", "message": "No eval run yet — POST /rag/eval/run"}
    return report


@router.post("/rag/eval/run")
async def rag_eval_run():
    from app.rag.eval.runner import run_rag_eval

    return await run_rag_eval()


@router.post("/rag/migrate/embeddings")
async def rag_migrate_embeddings():
    from app.rag.migration import reembed_stale_chunks

    return await reembed_stale_chunks()


@router.get("/overview/{ticker}")
async def intelligence_overview(ticker: str):
    """Combined news + filings + regime for ticker analysis UI."""
    regime_data = await regime.detect()
    return {
        "ticker": ticker.upper(),
        "news": await news.get_ticker_news(ticker),
        "filings": await filings.get_filings(ticker),
        "regime": regime_data,
        "ml": await ml.status(),
    }
