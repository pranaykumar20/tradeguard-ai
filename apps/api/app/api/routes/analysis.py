"""Ticker analysis endpoints."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.ml.features import compute_ticker_features
from app.ml.scoring import score_ticker
from app.risk.engine import RiskEngine

router = APIRouter()
risk_engine = RiskEngine()


class TickerAnalysis(BaseModel):
    ticker: str
    scores: dict[str, float]
    composite_score: float
    setup_label: str
    features: dict[str, float | str]
    risk_verdict: str
    warnings: list[str]


@router.get("/ticker/{ticker}", response_model=TickerAnalysis)
async def analyze_ticker(ticker: str):
    ticker = ticker.upper()
    features = compute_ticker_features(ticker)
    scores = score_ticker(features)
    verdict = risk_engine.evaluate_ticker(ticker, features, scores)
    return TickerAnalysis(
        ticker=ticker,
        scores=scores["components"],
        composite_score=scores["composite"],
        setup_label=scores["label"],
        features=features,
        risk_verdict=verdict.verdict,
        warnings=verdict.warnings,
    )


@router.get("/compare")
async def compare_tickers(tickers: str = Query(..., description="Comma-separated tickers")):
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    results = []
    for symbol in symbols[:6]:
        features = compute_ticker_features(symbol)
        scores = score_ticker(features)
        verdict = risk_engine.evaluate_ticker(symbol, features, scores)
        results.append(
            {
                "ticker": symbol,
                "composite_score": scores["composite"],
                "setup_label": scores["label"],
                "risk_verdict": verdict.verdict,
            }
        )
    return {"tickers": results}
