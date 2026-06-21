"""Chat intent detection — drives response layout selection."""

import re

from app.agents.tickers import extract_tickers, is_price_query

COMPARE_PATTERN = re.compile(
    r"\b(compare|vs\.?|versus|against)\b",
    re.I,
)
TRADE_SIDE_PATTERN = re.compile(r"\b(buy|sell|purchase|add)\b", re.I)
PORTFOLIO_PATTERN = re.compile(
    r"\b(portfolio|holdings|account|exposure|allocation|how am i doing|my risk)\b",
    re.I,
)


def detect_intent(message: str, tickers: list[str] | None = None) -> str:
    """Return layout key: trade | price | compare | portfolio | analysis | general."""
    tickers = tickers if tickers is not None else extract_tickers(message)

    if COMPARE_PATTERN.search(message) and len(tickers) >= 2:
        return "compare"
    if is_price_query(message) and tickers:
        return "price"
    if TRADE_SIDE_PATTERN.search(message) and tickers:
        return "trade"
    if not tickers:
        return "portfolio"
    if PORTFOLIO_PATTERN.search(message):
        return "portfolio"
    if tickers:
        return "analysis"
    return "general"
