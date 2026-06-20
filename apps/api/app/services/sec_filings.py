"""SEC filing summaries for RAG — Phase 6.3 + Phase 2 EDGAR."""

import structlog

from app.core.config import settings
from app.providers.sec.edgar import EdgarClient, mock_filing_documents
from app.rag.service import RAGService

logger = structlog.get_logger()


class SecFilingService:
    def __init__(self):
        self.rag = RAGService()
        self.edgar = EdgarClient()
        self._cache: dict[str, list[dict]] = {}

    async def _documents_for_ticker(self, ticker: str) -> list[dict]:
        ticker = ticker.upper()
        if ticker in self._cache:
            return self._cache[ticker]

        docs = await self.edgar.fetch_filing_documents(ticker)
        if not docs:
            docs = mock_filing_documents(ticker)
        self._cache[ticker] = docs
        return docs

    async def ensure_index(self) -> int:
        if not settings.sec_filings_enabled:
            return 0
        from app.rag.indexer import RAGIndexer

        return (await RAGIndexer().index_filings())

    async def get_filings(self, ticker: str) -> dict:
        ticker = ticker.upper()
        filings = await self._documents_for_ticker(ticker)
        rag_hits = await self.rag.search(f"{ticker} SEC filing risk factors", top_k=2, ticker=ticker)
        return {
            "ticker": ticker,
            "filing_count": len(filings),
            "filings": [
                {
                    "chunk_id": f.get("chunk_id", ""),
                    "source": f.get("source", ""),
                    "content": f.get("content", ""),
                }
                for f in filings
            ],
            "rag_excerpts": [
                {"source": h.source, "content": h.content, "score": h.score} for h in rag_hits
            ],
            "provider": filings[0]["meta"].get("provider", "unknown") if filings else "none",
        }

    async def search_filings(self, query: str, top_k: int = 3) -> list[dict]:
        hits = await self.rag.search(query, top_k=top_k)
        sec_hits = [
            h
            for h in hits
            if h.source
            and (
                "10-K" in h.source
                or "10-Q" in h.source
                or "SEC" in h.source
                or "Prospectus" in h.source
            )
        ]
        return [
            {"source": h.source, "content": h.content, "score": h.score}
            for h in (sec_hits or hits[:top_k])
        ]
