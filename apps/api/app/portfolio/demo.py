"""Demo portfolio for Phase 1 development without Robinhood MCP."""

def demo_portfolio() -> dict:
    return {
        "source": "demo",
        "account_value": 105_430.0,
        "buying_power": 32_850.0,
        "daily_pnl": 1250.0,
        "daily_pnl_pct": 1.2,
        "beta": 1.18,
        "max_drawdown_est": -12.6,
        "diversification": "Good",
        "cash_pct": 8.7,
        "positions": {
            "NVDA": {"shares": 45, "weight_pct": 18.2, "sector": "Technology"},
            "META": {"shares": 30, "weight_pct": 12.4, "sector": "Technology"},
            "MSFT": {"shares": 25, "weight_pct": 11.8, "sector": "Technology"},
            "QQQ": {"shares": 20, "weight_pct": 9.5, "sector": "Technology"},
        },
        "sector_exposure": {
            "Technology": 42.0,
            "Communication": 17.0,
            "Consumer Cyclical": 15.0,
            "Healthcare": 10.0,
            "Other": 16.0,
        },
    }
