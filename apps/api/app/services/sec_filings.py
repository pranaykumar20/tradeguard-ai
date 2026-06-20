"""SEC filing summaries for RAG — Phase 6.3."""

import structlog

from app.core.config import settings
from app.rag.service import RAGService

logger = structlog.get_logger()

FILING_SUMMARIES: dict[str, list[dict]] = {
    "NVDA": [
        {
            "chunk_id": "sec-nvda-10k-risk",
            "source": "NVDA 10-K Risk Factors (mock)",
            "content": (
                "NVDA faces concentration risk in data-center GPU demand, export controls on "
                "advanced chips to China, and customer concentration among hyperscalers. "
                "TradeGuard flags elevated single-name and tech sector exposure limits."
            ),
        },
        {
            "chunk_id": "sec-nvda-10k-mda",
            "source": "NVDA 10-K MD&A (mock)",
            "content": (
                "Revenue growth driven by AI accelerator shipments; gross margins sensitive to "
                "product mix and supply constraints. Monitor inventory levels and guidance revisions."
            ),
        },
    ],
    "MSFT": [
        {
            "chunk_id": "sec-msft-10k-cloud",
            "source": "MSFT 10-K (mock)",
            "content": (
                "Azure and Office 365 remain primary growth engines. Regulatory scrutiny on "
                "cloud bundling and AI copilot monetization are key watch items."
            ),
        },
    ],
    "META": [
        {
            "chunk_id": "sec-meta-10k-ads",
            "source": "META 10-K (mock)",
            "content": (
                "Advertising revenue tied to user engagement and Reels monetization. Reality Labs "
                "losses continue; capex rising for AI infrastructure."
            ),
        },
    ],
    "TSLA": [
        {
            "chunk_id": "sec-tsla-10k-margin",
            "source": "TSLA 10-K (mock)",
            "content": (
                "Automotive gross margins under pressure from price cuts and competition. "
                "Energy storage growth partially offsets; high volatility ticker — limit orders only."
            ),
        },
    ],
    "QQQ": [
        {
            "chunk_id": "sec-qqq-prospectus",
            "source": "QQQ Prospectus (mock)",
            "content": (
                "QQQ tracks Nasdaq-100 — heavy mega-cap tech weight. Use for diversified tech "
                "exposure vs single-name concentration; monitor index rebalance effects."
            ),
        },
    ],
    "GBTC": [
        {
            "chunk_id": "sec-gbtc-prospectus",
            "source": "GBTC Prospectus (mock)",
            "content": (
                "Spot bitcoin ETF exposure with premium/discount to NAV history. Crypto volatility "
                "regime strongly affects drawdowns — size positions conservatively."
            ),
        },
    ],
}


class SecFilingService:
    def __init__(self):
        self.rag = RAGService()

    async def ensure_index(self) -> int:
        if not settings.sec_filings_enabled:
            return 0
        docs = []
        for summaries in FILING_SUMMARIES.values():
            docs.extend(summaries)
        if not docs:
            return 0
        count = await self.rag.embed_and_store(docs)
        logger.info("sec_filings_indexed", chunks=count)
        return count

    async def get_filings(self, ticker: str) -> dict:
        ticker = ticker.upper()
        filings = FILING_SUMMARIES.get(ticker, [])
        rag_hits = await self.rag.search(f"{ticker} SEC filing risk factors", top_k=2)
        return {
            "ticker": ticker,
            "filing_count": len(filings),
            "filings": filings,
            "rag_excerpts": [
                {"source": h.source, "content": h.content, "score": h.score} for h in rag_hits
            ],
        }

    async def search_filings(self, query: str, top_k: int = 3) -> list[dict]:
        hits = await self.rag.search(query, top_k=top_k)
        sec_hits = [h for h in hits if h.source and ("10-K" in h.source or "10-Q" in h.source or "SEC" in h.source or "Prospectus" in h.source)]
        return [
            {"source": h.source, "content": h.content, "score": h.score}
            for h in (sec_hits or hits[:top_k])
        ]
