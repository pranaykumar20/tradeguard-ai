"""Tavily web search news provider tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.providers.news.factory import get_news_provider, reset_news_provider
from app.providers.news.tavily import TavilyNewsProvider
from app.services.news import NewsService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _reset_provider():
    reset_news_provider()
    yield
    reset_news_provider()


@pytest.mark.asyncio
async def test_tavily_parses_search_results(monkeypatch):
    monkeypatch.setattr(
        "app.providers.news.tavily.settings.tavily_api_key",
        "tvly-test",
    )

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "results": [
            {
                "title": "NVDA beats earnings expectations",
                "content": "NVIDIA reported strong data center growth.",
                "url": "https://reuters.com/nvda-earnings",
                "published_date": "2026-06-20T10:00:00Z",
            }
        ]
    }

    with patch("app.providers.news.tavily.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        headlines = await TavilyNewsProvider().get_headlines("NVDA", limit=3)

    assert len(headlines) == 1
    assert "NVDA" in headlines[0].title
    assert headlines[0].source == "reuters.com"
    assert headlines[0].sentiment > 50


@pytest.mark.asyncio
async def test_factory_prefers_tavily_in_auto(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.tavily_api_key", "tvly-test")
    monkeypatch.setattr("app.core.config.settings.polygon_api_key", "poly-test")
    monkeypatch.setattr("app.core.config.settings.news_provider", "auto")
    reset_news_provider()

    provider = get_news_provider()
    assert provider.provider_name == "tavily"


@pytest.mark.asyncio
async def test_search_for_chat_ticker(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.tavily_api_key", "tvly-test")

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "results": [
            {
                "title": "NVDA hits new high on AI demand",
                "content": "Chipmaker rally continues.",
                "url": "https://bloomberg.com/nvda",
                "published_date": "2026-06-20T10:00:00Z",
            }
        ]
    }

    with patch("app.providers.news.tavily.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        data = await NewsService().search_for_chat(
            "Should I buy more NVDA today?", ticker="NVDA", limit=3
        )

    assert data["live_search"] is True
    assert data["ticker"] == "NVDA"
    assert len(data["headlines"]) == 1


@pytest.mark.asyncio
async def test_search_for_chat_general(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.tavily_api_key", "tvly-test")

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "results": [
            {
                "title": "Tech sector weighs on S&P 500",
                "content": "Mega-cap tech led declines.",
                "url": "https://cnbc.com/markets",
                "published_date": "2026-06-20T10:00:00Z",
            }
        ]
    }

    with patch("app.providers.news.tavily.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        data = await NewsService().search_for_chat("What is my biggest portfolio risk?", limit=3)

    assert data["live_search"] is True
    assert data["headline_count"] == 1


@pytest.mark.asyncio
async def test_market_pulse_without_tavily():
    data = await NewsService().get_market_pulse(limit=5)
    assert data["live_search"] is False
    assert "hint" in data


@pytest.mark.asyncio
async def test_market_pulse_endpoint(client):
    resp = await client.get("/api/intelligence/market-news?limit=5")
    assert resp.status_code == 200
    assert "headlines" in resp.json()
