"""SEC EDGAR client — fetch and chunk 10-K sections for RAG."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import structlog

from app.core.config import settings
from app.rag.chunking import chunk_text, extract_section, strip_html

logger = structlog.get_logger()

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

ETF_TICKERS = frozenset({"QQQ", "GBTC", "SPY"})

MOCK_FILING_SUMMARIES: dict[str, list[dict]] = {
    "QQQ": [
        {
            "chunk_id": "sec-qqq-prospectus",
            "source": "QQQ Prospectus (mock)",
            "content": (
                "QQQ tracks Nasdaq-100 — heavy mega-cap tech weight. Use for diversified tech "
                "exposure vs single-name concentration; monitor index rebalance effects."
            ),
            "meta": {"type": "filing", "ticker": "QQQ", "form": "prospectus", "section": "overview"},
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
            "meta": {"type": "filing", "ticker": "GBTC", "form": "prospectus", "section": "overview"},
        },
    ],
}


class EdgarClient:
    def __init__(self):
        self._ticker_map: dict[str, str] | None = None

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": settings.sec_edgar_user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

    async def _get_json(self, url: str) -> dict | list:
        async with httpx.AsyncClient(timeout=30.0, headers=self._headers()) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def _get_text(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=60.0, headers=self._headers()) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def _load_ticker_map(self) -> dict[str, str]:
        if self._ticker_map is not None:
            return self._ticker_map
        data = await self._get_json(COMPANY_TICKERS_URL)
        mapping: dict[str, str] = {}
        for entry in data.values():
            ticker = str(entry["ticker"]).upper()
            mapping[ticker] = str(entry["cik_str"]).zfill(10)
        self._ticker_map = mapping
        return mapping

    async def resolve_cik(self, ticker: str) -> str | None:
        mapping = await self._load_ticker_map()
        return mapping.get(ticker.upper())

    async def _latest_10k_filing(self, cik: str) -> dict | None:
        payload = await self._get_json(SUBMISSIONS_URL.format(cik=cik))
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        filing_dates = recent.get("filingDate", [])

        for index, form in enumerate(forms):
            if form != "10-K":
                continue
            return {
                "form": form,
                "accession": accessions[index],
                "primary_document": primary_docs[index],
                "filing_date": filing_dates[index],
            }
        return None

    def _filing_document_url(self, cik: str, accession: str, primary_document: str) -> str:
        cik_int = str(int(cik))
        accession_clean = accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_clean}/{primary_document}"

    def _extract_sections(self, raw_html: str) -> dict[str, str]:
        text = strip_html(raw_html)
        sections = {
            "risk_factors": extract_section(
                text,
                r"Item\s+1A\.?\s*Risk\s+Factors",
                r"Item\s+1B\.|Item\s+2\.|Unresolved\s+Staff\s+Comments",
            ),
            "mda": extract_section(
                text,
                r"Item\s+7\.?\s*Management['\u2019]?s\s+Discussion\s+and\s+Analysis",
                r"Item\s+7A\.|Item\s+8\.|Quantitative\s+and\s+Qualitative",
            ),
        }
        return {key: value for key, value in sections.items() if value}

    def _section_documents(
        self,
        ticker: str,
        filing: dict,
        sections: dict[str, str],
    ) -> list[dict]:
        documents: list[dict] = []
        filed_at = filing.get("filing_date")
        for section_name, body in sections.items():
            for index, chunk in enumerate(chunk_text(body), start=1):
                slug = section_name.replace("_", "-")
                documents.append(
                    {
                        "chunk_id": f"sec-{ticker.lower()}-10k-{slug}-{index:02d}",
                        "source": f"{ticker} 10-K {section_name.replace('_', ' ').title()} (SEC EDGAR)",
                        "content": chunk,
                        "meta": {
                            "type": "filing",
                            "ticker": ticker.upper(),
                            "form": "10-K",
                            "section": section_name,
                            "filed_at": filed_at,
                            "provider": "sec_edgar",
                        },
                    }
                )
        return documents

    async def fetch_filing_documents(self, ticker: str) -> list[dict]:
        ticker = ticker.upper()
        if ticker in ETF_TICKERS:
            return list(MOCK_FILING_SUMMARIES.get(ticker, []))

        if not settings.sec_edgar_enabled:
            return []

        try:
            cik = await self.resolve_cik(ticker)
            if not cik:
                logger.warning("edgar_cik_not_found", ticker=ticker)
                return []

            filing = await self._latest_10k_filing(cik)
            if not filing:
                logger.warning("edgar_10k_not_found", ticker=ticker, cik=cik)
                return []

            doc_url = self._filing_document_url(
                cik, filing["accession"], filing["primary_document"]
            )
            raw_html = await self._get_text(doc_url)
            sections = self._extract_sections(raw_html)
            if not sections:
                logger.warning("edgar_sections_empty", ticker=ticker, url=doc_url)
                return []

            docs = self._section_documents(ticker, filing, sections)
            logger.info(
                "edgar_filing_fetched",
                ticker=ticker,
                chunks=len(docs),
                filed_at=filing.get("filing_date"),
            )
            return docs
        except Exception as exc:
            logger.warning("edgar_fetch_failed", ticker=ticker, error=str(exc))
            return []


def mock_filing_documents(ticker: str) -> list[dict]:
    """Offline fallback summaries when EDGAR is unavailable."""
    ticker = ticker.upper()
    if ticker in MOCK_FILING_SUMMARIES:
        return list(MOCK_FILING_SUMMARIES[ticker])

    generic = {
        "NVDA": "GPU and AI accelerator demand with export control and customer concentration risks.",
        "MSFT": "Cloud and productivity growth with regulatory scrutiny on bundling and AI monetization.",
        "META": "Advertising revenue tied to engagement; Reality Labs losses and rising AI capex.",
        "TSLA": "Automotive margins under pressure; high volatility — limit orders only.",
    }
    blurb = generic.get(ticker)
    if not blurb:
        return []

    return [
        {
            "chunk_id": f"sec-{ticker.lower()}-10k-mock",
            "source": f"{ticker} 10-K Summary (mock)",
            "content": blurb,
            "meta": {
                "type": "filing",
                "ticker": ticker,
                "form": "10-K",
                "section": "summary",
                "provider": "mock",
                "filed_at": datetime.now(timezone.utc).date().isoformat(),
            },
        }
    ]
