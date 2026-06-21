"""Tests for chat response builder and intent detection."""

from app.agents.intent import detect_intent
from app.agents.response_builder import (
    build_portfolio_response,
    build_ticker_analysis,
    extract_llm_summary,
    structured_to_markdown,
)
from app.risk.engine import RiskVerdict


def test_detect_intent_trade():
    assert detect_intent("Should I buy more NVDA today?", ["NVDA"]) == "trade"


def test_detect_intent_price():
    assert detect_intent("What is NVDA trading at?", ["NVDA"]) == "price"


def test_detect_intent_compare():
    assert detect_intent("Compare NVDA vs META", ["NVDA", "META"]) == "compare"


def test_detect_intent_portfolio():
    assert detect_intent("How is my portfolio doing?", []) == "portfolio"


def test_build_ticker_analysis_structure():
    verdict = RiskVerdict(verdict="CAUTION", warnings=["Tech exposure high"], blocks=[])
    structured = build_ticker_analysis(
        layout="trade",
        ticker="NVDA",
        features={"last_price": 100.0, "qqq_trend": "bearish", "rsi_14": 55},
        scores={
            "composite": 52,
            "label": "Watch",
            "components": {"technical": 55, "macro": 38, "news": 50, "ml": 60, "risk": 45},
        },
        verdict=verdict,
        snapshot={
            "risk_label": "Moderate",
            "risk_score": 48,
            "sector_exposure": {"Technology": 42.0},
        },
        tech_limit=30.0,
    )

    assert structured["layout"] == "trade"
    assert "NVDA" in structured["summary"]
    assert len(structured["factors"]) >= 2
    assert len(structured["snapshot"]) == 4
    assert len(structured["scores"]) == 5


def test_structured_to_markdown_includes_summary():
    structured = build_portfolio_response(
        snapshot={
            "risk_label": "Moderate",
            "risk_score": 48,
            "portfolio_value": 100000,
            "beta": 1.1,
            "daily_pnl": 250,
            "sector_exposure": {"Technology": 35.0},
            "alerts": [],
        },
        warnings=[],
    )
    md = structured_to_markdown(structured)
    assert "**" in md
    assert "Snapshot" in md


def test_extract_llm_summary():
    reply = "**I don't recommend buying more NVDA today.**\n\nSome extra context."
    assert extract_llm_summary(reply) == "I don't recommend buying more NVDA today."
