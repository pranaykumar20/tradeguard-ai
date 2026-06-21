"""Ticker analysis endpoints."""

import asyncio

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.ml.scoring import score_ticker
from app.risk.engine import RiskEngine
from app.services.features import compute_ticker_features
from app.services.news import NewsService
from app.services.regime import RegimeService
from app.services.sec_filings import SecFilingService

router = APIRouter()
risk_engine = RiskEngine()
news_service = NewsService()
filing_service = SecFilingService()
regime_service = RegimeService()


class NewsHeadlineOut(BaseModel):
    title: str
    summary: str
    source: str
    published_at: str
    sentiment: float


class TickerAnalysis(BaseModel):
    ticker: str
    scores: dict[str, float]
    composite_score: float
    setup_label: str
    features: dict[str, float | str]
    risk_verdict: str
    warnings: list[str]
    news: dict | None = None
    filings: dict | None = None
    regime: dict | None = None
    composite_score_adjusted: float | None = None


@router.get("/ticker/{ticker}", response_model=TickerAnalysis)
async def analyze_ticker(ticker: str):
    ticker = ticker.upper()
    regime_data = await regime_service.detect()
    features = await compute_ticker_features(ticker)
    features["ml_vol_prob"] = regime_data.get("ml_vol_prob", 0)
    features["ml_vol_confidence"] = regime_data.get("ml_vol_confidence", 0)
    scores = score_ticker(features, ticker)
    adjusted = regime_service.apply_to_score(scores["composite"], regime_data)
    verdict = risk_engine.evaluate_ticker(
        ticker, features, scores, regime=regime_data
    )
    news = await news_service.get_ticker_news(ticker)
    filing_data = await filing_service.get_filings(ticker)
    result = TickerAnalysis(
        ticker=ticker,
        scores=scores["components"],
        composite_score=scores["composite"],
        composite_score_adjusted=adjusted,
        setup_label=scores["label"],
        features=features,
        risk_verdict=verdict.verdict,
        warnings=verdict.warnings,
        news=news,
        filings=filing_data,
        regime=regime_data,
    )
    asyncio.create_task(_index_analysis_snapshot(result))
    return result


async def _index_analysis_snapshot(result: TickerAnalysis) -> None:
    try:
        from app.rag.indexers.analysis_snapshot import index_analysis_snapshot

        await index_analysis_snapshot(result.model_dump())
    except Exception:
        pass


@router.get("/compare")
async def compare_tickers(tickers: str = Query(..., description="Comma-separated tickers")):
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    regime_data = await regime_service.detect()
    results = []
    for symbol in symbols[:6]:
        features = await compute_ticker_features(symbol)
        features["ml_vol_prob"] = regime_data.get("ml_vol_prob", 0)
        features["ml_vol_confidence"] = regime_data.get("ml_vol_confidence", 0)
        scores = score_ticker(features, symbol)
        verdict = risk_engine.evaluate_ticker(symbol, features, scores, regime=regime_data)
        results.append(
            {
                "ticker": symbol,
                "composite_score": scores["composite"],
                "composite_score_adjusted": regime_service.apply_to_score(
                    scores["composite"], regime_data
                ),
                "setup_label": scores["label"],
                "risk_verdict": verdict.verdict,
            }
        )
    return {"tickers": results, "regime": regime_data}
