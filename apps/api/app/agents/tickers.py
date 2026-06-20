"""Ticker extraction from chat messages — symbols and company names."""

import re

from app.risk.rules import default_rules

SYMBOL_PATTERN = re.compile(
    r"\b(" + "|".join(default_rules().allowed_tickers + ["AAPL", "SPY", "SMH"]) + r")\b",
    re.I,
)

# Common company names → tickers (allowed universe + frequent aliases)
COMPANY_TO_TICKER: dict[str, str] = {
    "nvidia": "NVDA",
    "microsoft": "MSFT",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "bitcoin": "GBTC",
    "grayscale bitcoin": "GBTC",
}

PRICE_QUERY_PATTERN = re.compile(
    r"\b("
    r"price|stock price|share price|trading at|traded at|current price|"
    r"live price|how much is|how much does|what is .* trading|quote"
    r")\b",
    re.I,
)


def extract_tickers(message: str) -> list[str]:
    """Return unique tickers from symbols (NVDA) or company names (Tesla)."""
    found: list[str] = []
    for match in SYMBOL_PATTERN.findall(message):
        found.append(match.upper())

    lower = message.lower()
    for name, ticker in COMPANY_TO_TICKER.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            found.append(ticker)

    return list(dict.fromkeys(found))


def is_price_query(message: str) -> bool:
    return bool(PRICE_QUERY_PATTERN.search(message))
