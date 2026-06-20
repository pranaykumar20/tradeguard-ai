"""Market quote service tests."""

from app.services.market_quotes import format_price_for_context


def test_format_price_for_context():
    quote = {
        "ticker": "TSLA",
        "last_price": 250.5,
        "change_pct": 1.2,
        "volume": 1_000_000,
        "provider": "polygon",
        "live": True,
    }
    web = {
        "answer": "TSLA is trading around $250.",
        "provider": "tavily",
        "sources": [{"title": "Tesla Stock Price", "url": "https://example.com"}],
    }
    text = format_price_for_context(quote, web)
    assert "TSLA" in text
    assert "$250.50" in text
    assert "Web search" in text
