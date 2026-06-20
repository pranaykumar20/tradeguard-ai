"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TradeGuard AI"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://tradeguard:tradeguard@localhost:5433/tradeguard"
    redis_url: str = "redis://localhost:6380/0"
    celery_broker_url: str = "redis://localhost:6380/1"
    celery_result_backend: str = "redis://localhost:6380/2"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    robinhood_mcp_url: str = ""
    robinhood_mcp_enabled: bool = False

    polygon_api_key: str = ""
    fred_api_key: str = ""

    risk_max_trade_usd: float = 250.0
    risk_max_daily_loss_usd: float = 50.0
    risk_max_single_name_pct: float = 20.0
    risk_max_tech_sector_pct: float = 30.0
    risk_require_manual_approval: bool = True
    risk_allow_options: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
