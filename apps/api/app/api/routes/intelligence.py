"""Intelligence API — news, filings, regime, ML retrain (Phase 6)."""

from fastapi import APIRouter, HTTPException

from app.services.ml_retrain import MLRetrainService
from app.services.news import NewsService
from app.services.regime import RegimeService
from app.services.sec_filings import SecFilingService

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
