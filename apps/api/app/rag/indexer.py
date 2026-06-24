"""Unified RAG index refresh — playbooks, SEC filings, news."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import structlog

from app.core.config import settings
from app.core.user_context import for_each_user
from app.db.storage import get_storage
from app.providers.news.factory import get_news_provider
from app.providers.sec.edgar import EdgarClient, mock_filing_documents
from app.rag.pipeline import RAGIngestPipeline
from app.rag.playbooks import load_playbook_documents
from app.rag.schemas import RAG_SOURCES
from app.rag.service import RAGService
from app.risk.rules import default_rules

logger = structlog.get_logger()

_RAG_INIT_KEY = "rag_initialized"


class RAGIndexer:
    def __init__(self):
        self.pipeline = RAGIngestPipeline()
        self.edgar = EdgarClient()

    @property
    def tickers(self) -> list[str]:
        return list(default_rules().allowed_tickers)

    async def index_playbooks(self) -> int:
        documents = load_playbook_documents()
        if not documents:
            return 0
        result = await self.pipeline.ingest(documents)
        logger.info("rag_playbooks_indexed", **result)
        return int(result["stored"])

    async def index_filings(self) -> int:
        if not settings.sec_filings_enabled:
            return 0

        documents: list[dict] = []
        for ticker in self.tickers:
            docs = await self.edgar.fetch_filing_documents(ticker)
            if not docs:
                docs = mock_filing_documents(ticker)
            documents.extend(docs)

        if not documents:
            return 0
        result = await self.pipeline.ingest(documents)
        logger.info("rag_filings_indexed", stored=result["stored"], tickers=len(self.tickers))
        return int(result["stored"])

    async def index_regime(self) -> int:
        if not settings.rag_regime_index_enabled:
            return 0
        from app.rag.indexers.regime_snapshot import index_regime_snapshot

        return await index_regime_snapshot()

    async def evict_stale_news(self) -> int:
        storage = await get_storage()
        deleted = await storage.delete_stale_rag_news(older_than_days=settings.rag_news_ttl_days)
        if deleted:
            from app.rag.cache import invalidate_rag_caches

            invalidate_rag_caches()
        logger.info("rag_news_evicted", deleted=deleted, ttl_days=settings.rag_news_ttl_days)
        return deleted

    async def index_news(self) -> int:
        if not settings.rag_news_index_enabled:
            return 0

        provider = get_news_provider()
        documents: list[dict] = []
        for ticker in self.tickers:
            headlines = await provider.get_headlines(ticker, limit=settings.rag_news_headline_limit)
            for headline in headlines:
                title = headline.title.strip()
                if not title:
                    continue
                digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:10]
                documents.append(
                    {
                        "chunk_id": f"news-{ticker.lower()}-{digest}",
                        "source": f"{ticker} news — {headline.source}",
                        "content": title,
                        "meta": {
                            "type": "news",
                            "ticker": ticker,
                            "title": title,
                            "summary": (headline.summary or "").strip(),
                            "source_name": headline.source,
                            "published_at": headline.published_at,
                            "sentiment": headline.sentiment,
                            "url": headline.url,
                            "visibility": "global",
                        },
                    }
                )

        if not documents:
            return 0
        result = await self.pipeline.ingest(documents)
        logger.info("rag_news_indexed", stored=result["stored"], tickers=len(self.tickers))
        return int(result["stored"])

    async def index_journal(self) -> int:
        if not settings.rag_journal_index_enabled:
            return 0
        from app.rag.journal_index import index_user_journal

        counts = await for_each_user(index_user_journal)
        total = sum(counts)
        logger.info("rag_journal_indexed", chunks=total, users=len(counts))
        return total

    async def refresh_source(self, source: str) -> dict:
        if source == "all":
            return await self.refresh_all()
        if source not in RAG_SOURCES:
            raise ValueError(f"Unknown RAG source: {source}")

        handlers = {
            "playbooks": self.index_playbooks,
            "filings": self.index_filings,
            "news": self.index_news,
            "journal": self.index_journal,
            "regime": self.index_regime,
        }
        count = await handlers[source]()
        RAGService.mark_ready()
        return {"source": source, "stored": count}

    async def refresh_all(self) -> dict:
        playbooks = await self.index_playbooks()
        filings = await self.index_filings()
        news = await self.index_news()
        journal = await self.index_journal()
        regime = await self.index_regime()
        evicted = await self.evict_stale_news()
        storage = await get_storage()
        await storage.set_app_state(
            _RAG_INIT_KEY,
            {"initialized_at": datetime.now(timezone.utc).isoformat()},
        )
        RAGService.mark_ready()
        result = {
            "playbooks": playbooks,
            "filings": filings,
            "news": news,
            "journal": journal,
            "regime": regime,
            "news_evicted": evicted,
            "total": playbooks + filings + news + journal + regime,
        }
        logger.info("rag_index_refreshed", **result)
        return result

    async def ensure_initialized(self) -> dict:
        """Sync playbooks from disk; index filings/news once, then on Celery schedule."""
        storage = await get_storage()
        playbooks = await self.index_playbooks()
        initialized = await storage.get_app_state(_RAG_INIT_KEY)
        if initialized:
            RAGService.mark_ready()
            return {"status": "already_indexed", "playbooks": playbooks}

        filings = await self.index_filings()
        news = await self.index_news()
        journal = await self.index_journal()
        await storage.set_app_state(
            _RAG_INIT_KEY,
            {"initialized_at": datetime.now(timezone.utc).isoformat()},
        )
        RAGService.mark_ready()
        return {
            "status": "initialized",
            "playbooks": playbooks,
            "filings": filings,
            "news": news,
            "journal": journal,
            "total": playbooks + filings + news + journal,
        }
