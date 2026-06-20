"""Phase 2 RAG — richer corpus ingestion."""

from pathlib import Path

import pytest

from app.providers.sec.edgar import EdgarClient, mock_filing_documents
from app.rag.chunking import chunk_text, extract_section, strip_html
from app.rag.playbooks import _parse_markdown_sections, load_playbook_documents


def test_parse_markdown_sections():
    text = "# Title\n\nIntro ignored.\n\n## Rule A\n\nFirst rule.\n\n## Rule B\n\nSecond rule."
    sections = _parse_markdown_sections(text)
    assert len(sections) == 3
    assert sections[1] == ("Rule A", "First rule.")
    assert sections[2] == ("Rule B", "Second rule.")


def test_load_playbooks_from_directory(tmp_path: Path):
    md = tmp_path / "risk-playbook.md"
    md.write_text(
        "# Risk\n\n## Circuit breaker\n\nHalt trading when daily loss limit is hit.\n",
        encoding="utf-8",
    )
    docs = load_playbook_documents(tmp_path)
    assert len(docs) == 1
    assert docs[0]["meta"]["type"] == "playbook"
    assert "daily loss" in docs[0]["content"]


def test_chunk_text_splits_long_body():
    body = ". ".join(["Sentence number %d" % i for i in range(80)])
    chunks = chunk_text(body, max_chars=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 220 for chunk in chunks)


def test_strip_html_and_extract_section():
    html = """
    <html><body>
    Item 1A. Risk Factors
    <p>Export controls may limit chip sales.</p>
    Item 1B. Unresolved Staff Comments
    </body></html>
    """
    text = strip_html(html)
    section = extract_section(
        text,
        r"Item\s+1A\.?\s*Risk\s+Factors",
        r"Item\s+1B\.|Item\s+2\.",
    )
    assert "Export controls" in section


def test_edgar_extract_sections():
    client = EdgarClient()
    raw = """
    Item 1A. Risk Factors We face supply chain risk and competition.
    Item 1B. Unresolved Staff Comments None.
    Item 7. Management's Discussion and Analysis Revenue grew 20 percent year over year.
    Item 7A. Quantitative and Qualitative Disclosures About Market Risk
    """
    sections = client._extract_sections(raw)
    assert "supply chain" in sections["risk_factors"].lower()
    assert "revenue grew" in sections["mda"].lower()


def test_mock_filing_documents_for_equity():
    docs = mock_filing_documents("NVDA")
    assert len(docs) == 1
    assert docs[0]["meta"]["ticker"] == "NVDA"


@pytest.mark.asyncio
async def test_rag_indexer_refresh_all(monkeypatch):
    from app.rag.indexer import RAGIndexer

    monkeypatch.setattr("app.rag.indexer.settings.sec_filings_enabled", True)
    monkeypatch.setattr("app.rag.indexer.settings.rag_news_index_enabled", True)
    monkeypatch.setattr("app.rag.indexer.settings.sec_edgar_enabled", False)

    async def fake_filings(_self, ticker: str):
        return mock_filing_documents(ticker)

    class FakeNews:
        provider_name = "mock"

        async def get_headlines(self, ticker: str, limit: int = 8):
            from app.providers.news.base import NewsHeadline

            return [
                NewsHeadline(
                    title=f"{ticker} beats estimates",
                    summary="",
                    source="MockWire",
                    published_at="2026-06-01T12:00:00Z",
                    sentiment=60.0,
                )
            ]

    monkeypatch.setattr("app.rag.indexer.EdgarClient.fetch_filing_documents", fake_filings)
    monkeypatch.setattr("app.rag.indexer.get_news_provider", lambda: FakeNews())

    indexer = RAGIndexer()
    result = await indexer.refresh_all()
    assert result["playbooks"] >= 7
    assert result["filings"] >= 6
    assert result["news"] >= 6
