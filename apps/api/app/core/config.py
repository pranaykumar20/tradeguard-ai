"""Application configuration."""

import json

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(value: str) -> list[str]:
    stripped = value.strip()
    if stripped.startswith("["):
        return json.loads(stripped)
    return [origin.strip() for origin in stripped.split(",") if origin.strip()]


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

    # auto = use live provider when API key is set, otherwise mock
    market_data_provider: str = "auto"
    embedding_provider: str = "auto"
    storage_backend: str = "auto"  # auto | postgres | memory

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    mcp_provider: str = "auto"  # auto | mock | live
    robinhood_mcp_url: str = ""
    robinhood_mcp_enabled: bool = False

    polygon_api_key: str = ""
    polygon_base_url: str = "https://api.polygon.io"
    fred_api_key: str = ""

    risk_max_trade_usd: float = 250.0
    risk_max_daily_loss_usd: float = 50.0
    risk_max_single_name_pct: float = 20.0
    risk_max_tech_sector_pct: float = 30.0
    risk_require_manual_approval: bool = True
    risk_allow_options: bool = False

    market_refresh_interval_minutes: int = 15
    paper_trade_goal: int = 100
    memory_store_path: str = ".data/tradeguard_store.json"

    # Phase 4 — monitoring & alerts (auto = slack when webhook set, otherwise mock)
    alert_provider: str = "auto"
    monitoring_enabled: bool = True
    monitoring_interval_minutes: int = 5
    trading_halt_on_daily_loss: bool = True
    max_drawdown_alert_pct: float = 8.0
    slack_webhook_url: str = ""
    alert_email_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Phase 4.2 — semi-automated strategies
    strategies_enabled: bool = True
    strategies_auto_execute: bool = True
    strategy_eval_interval_minutes: int = 30

    # Phase 4.3 — performance validation gate (blocks Phase 4.4 automation)
    validation_gate_enabled: bool = True
    validation_dev_bypass: bool = False
    validation_allow_demo_seed: bool = True
    validation_min_months: float = 3.0
    validation_min_sharpe: float = 0.5
    validation_max_drawdown_pct: float = 15.0
    validation_min_win_rate: float = 45.0
    validation_min_total_pnl: float = 0.0
    validation_max_rule_violations: int = 10
    validation_min_filled_trades: int = 20
    validation_starting_capital: float = 10_000.0

    # Phase 4.4 — constrained automation
    automation_feature_enabled: bool = True
    automation_max_daily_trades: int = 5

    cors_origins_env: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        validation_alias="CORS_ORIGINS",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return _parse_cors_origins(self.cors_origins_env)

    @property
    def use_polygon(self) -> bool:
        if self.market_data_provider == "mock":
            return False
        if self.market_data_provider == "polygon":
            return bool(self.polygon_api_key)
        return bool(self.polygon_api_key)

    @property
    def use_openai_embeddings(self) -> bool:
        if self.embedding_provider == "mock":
            return False
        if self.embedding_provider == "openai":
            return bool(self.openai_api_key)
        return bool(self.openai_api_key)

    @property
    def active_market_provider(self) -> str:
        return "polygon" if self.use_polygon else "mock"

    @property
    def active_embedding_provider(self) -> str:
        return "openai" if self.use_openai_embeddings else "mock"

    @property
    def active_storage_backend(self) -> str:
        if self.storage_backend in {"postgres", "memory"}:
            return self.storage_backend
        return "postgres"

    @property
    def use_live_mcp(self) -> bool:
        if not self.robinhood_mcp_enabled:
            return False
        if self.mcp_provider == "mock":
            return False
        if self.mcp_provider == "live":
            return bool(self.robinhood_mcp_url)
        return bool(self.robinhood_mcp_url)

    @property
    def active_mcp_provider(self) -> str:
        return "live" if self.use_live_mcp else "mock"

    @property
    def use_slack_alerts(self) -> bool:
        if self.alert_provider == "mock":
            return False
        if self.alert_provider == "slack":
            return bool(self.slack_webhook_url)
        return bool(self.slack_webhook_url)

    @property
    def active_alert_provider(self) -> str:
        return "slack" if self.use_slack_alerts else "mock"


settings = Settings()
