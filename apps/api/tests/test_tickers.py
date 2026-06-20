"""Ticker and price query helpers for chat."""

from app.agents.tickers import extract_tickers, is_price_query


def test_extract_tesla_from_company_name():
    assert extract_tickers("tell me the current Tesla stock price") == ["TSLA"]


def test_extract_symbol():
    assert extract_tickers("What about NVDA?") == ["NVDA"]


def test_is_price_query():
    assert is_price_query("What is the Tesla stock price?")
    assert not is_price_query("Should I buy more NVDA today?")
