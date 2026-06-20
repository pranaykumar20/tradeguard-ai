"""Phase 6 — intelligence upgrade tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.news import NewsService
from app.services.regime import RegimeService
from app.services.sec_filings import SecFilingService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_news_service_mock():
    data = await NewsService().get_ticker_news("NVDA")
    assert data["ticker"] == "NVDA"
    assert data["headline_count"] >= 1
    assert 0 <= data["sentiment_score"] <= 100
    assert data["provider"] == "mock"


@pytest.mark.asyncio
async def test_regime_detection():
    data = await RegimeService().detect()
    assert data["regime"] in {"risk_on", "neutral", "risk_off", "high_vol"}
    assert "label" in data
    assert "signals" in data


@pytest.mark.asyncio
async def test_regime_score_adjustment():
    svc = RegimeService()
    adjusted = svc.apply_to_score(70, {"risk_score_adjustment": -8})
    assert adjusted == 62.0


@pytest.mark.asyncio
async def test_sec_filings_for_nvda():
    svc = SecFilingService()
    await svc.ensure_index()
    data = await svc.get_filings("NVDA")
    assert data["ticker"] == "NVDA"
    assert data["filing_count"] >= 1


@pytest.mark.asyncio
async def test_intelligence_regime_endpoint(client):
    resp = await client.get("/api/intelligence/regime")
    assert resp.status_code == 200
    assert "regime" in resp.json()


@pytest.mark.asyncio
async def test_intelligence_news_endpoint(client):
    resp = await client.get("/api/intelligence/news/MSFT")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "MSFT"
    assert data["headlines"]


@pytest.mark.asyncio
async def test_analysis_includes_intelligence(client):
    resp = await client.get("/api/analysis/ticker/NVDA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["news"] is not None
    assert data["filings"] is not None
    assert data["regime"] is not None


@pytest.mark.asyncio
async def test_ml_status_endpoint(client):
    resp = await client.get("/api/intelligence/ml/status")
    assert resp.status_code == 200
    assert "model_exists" in resp.json()


@pytest.mark.asyncio
async def test_health_phase_6(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["phase"] == 6
