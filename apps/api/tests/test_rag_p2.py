"""Phase 5 P2 — query router and structured agent tools."""

from app.rag.router import plan_query
from app.rag.tools import infer_rag_tools


def test_plan_query_price_uses_direct_call():
    plan = plan_query("What is NVDA trading at?", tickers=["NVDA"])
    assert "get_quote" in plan.direct_calls
    assert plan.tickers == ["NVDA"]
    assert plan.freshness == "live"


def test_plan_query_trade_history():
    plan = plan_query("Show my recent paper trades")
    assert "query_trades" in plan.direct_calls


def test_plan_query_buy_includes_risk_check():
    plan = plan_query("Should I buy more NVDA today?", tickers=["NVDA"])
    assert "check_risk_limits" in plan.direct_calls
    assert "search_playbooks" in plan.rag_tools


def test_plan_query_filing_uses_rag():
    plan = plan_query("What are NVDA 10-K risk factors?", tickers=["NVDA"])
    assert "search_filings" in plan.rag_tools


def test_plan_query_temporal_freshness():
    plan = plan_query("What did we think about NVDA last month?", tickers=["NVDA"])
    assert plan.freshness == "historical"
    assert "search_analysis_history" in plan.rag_tools


def test_infer_rag_tools_unchanged_for_trade_question():
    tools = infer_rag_tools("Should I buy more NVDA today?")
    assert "search_playbooks" in tools
