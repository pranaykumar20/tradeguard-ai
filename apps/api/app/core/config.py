"""Application configuration."""

import json

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(value: str) -> str:
    """Railway/Fly often provide postgres:// — async SQLAlchemy needs asyncpg driver."""
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+asyncpg://", 1)
    if value.startswith("postgresql://") and "+asyncpg" not in value:
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    return value


def _parse_cors_origins(value: str) -> list[str]:
    stripped = value.strip()
    if stripped.startswith("["):
        return json.loads(stripped)
    return [origin.strip() for origin in stripped.split(",") if origin.strip()]


def _redis_db_url(redis_url: str, db: int) -> str:
    """Build redis://…/N, replacing any existing trailing database index."""
    base = redis_url.rstrip("/")
    last = base.rsplit("/", 1)[-1]
    if last.isdigit():
        base = base.rsplit("/", 1)[0]
    return f"{base}/{db}"


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

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, value: str) -> str:
        if isinstance(value, str):
            return _normalize_database_url(value)
        return value
    redis_url: str = "redis://localhost:6380/0"
    celery_broker_url: str = "redis://localhost:6380/1"
    celery_result_backend: str = "redis://localhost:6380/2"

    @model_validator(mode="after")
    def derive_celery_from_redis(self) -> "Settings":
        """When REDIS_URL is set (e.g. Railway), default Celery URLs to /1 and /2 on same host."""
        if self.redis_url == "redis://localhost:6380/0":
            return self
        if self.celery_broker_url == "redis://localhost:6380/1":
            self.celery_broker_url = _redis_db_url(self.redis_url, 1)
        if self.celery_result_backend == "redis://localhost:6380/2":
            self.celery_result_backend = _redis_db_url(self.redis_url, 2)
        return self

    # auto = use live provider when API key is set, otherwise mock
    market_data_provider: str = "auto"
    embedding_provider: str = "auto"
    storage_backend: str = "auto"  # auto | postgres | memory

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cursor_api_key: str = ""
    llm_model: str = "composer-2.5"
    llm_provider: str = "cursor"  # cursor | openai | anthropic
    cursor_workspace: str = ""  # local bridge cwd; defaults to repo root
    cursor_cloud_repo_url: str = ""  # optional — use cloud agents when set (production)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    mcp_provider: str = "auto"  # auto | mock | live
    robinhood_mcp_url: str = ""
    robinhood_mcp_default_url: str = "https://agent.robinhood.com/mcp/trading"
    robinhood_mcp_enabled: bool = False
    api_public_url: str = ""
    frontend_url: str = ""
    secrets_encryption_key: str = ""

    polygon_api_key: str = ""
    polygon_base_url: str = "https://api.polygon.io"
    fred_api_key: str = ""

    tavily_api_key: str = ""
    tavily_search_depth: str = "basic"  # basic | advanced
    tavily_news_days: int = 3

    risk_max_trade_usd: float = 250.0
    risk_max_daily_loss_usd: float = 50.0
    risk_max_single_name_pct: float = 20.0
    risk_max_tech_sector_pct: float = 30.0
    risk_require_manual_approval: bool = True
    risk_allow_options: bool = False

    # Phase 7 — execution & portfolio expansion
    multi_broker_enabled: bool = True
    default_broker_id: str = "robinhood_agentic"
    options_workflow_enabled: bool = True
    risk_max_option_trade_usd: float = 100.0
    tax_lot_tracking_enabled: bool = True
    wash_sale_window_days: int = 30

    # Phase 8 — observability & compliance
    audit_export_max_days: int = 90
    platform_latency_threshold_ms: float = 2000.0
    model_drift_threshold: float = 0.05
    platform_health_check_enabled: bool = True

    # Phase 9 — product & UX
    push_notifications_enabled: bool = True
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:ops@tradeguard.ai"

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
    alert_email_from: str = ""

    # Phase 5.2 — auth (disabled when CLERK_SECRET_KEY empty)
    auth_provider: str = "auto"  # auto | disabled | clerk
    clerk_secret_key: str = ""
    clerk_jwt_issuer: str = ""  # e.g. https://your-app.clerk.accounts.dev
    platform_admin_emails: str = ""  # comma-separated bootstrap admins

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

    # Phase 6 — intelligence
    news_provider: str = "auto"  # auto | mock | polygon | tavily
    rag_top_k: int = 3
    rag_playbooks_dir: str = ""
    rag_news_index_enabled: bool = True
    rag_news_headline_limit: int = 5
    rag_refresh_enabled: bool = True
    rag_refresh_interval_minutes: int = 360
    rag_hybrid_search_enabled: bool = True
    rag_query_rewrite_enabled: bool = True
    rag_type_routing_enabled: bool = True
    rag_recency_decay_enabled: bool = True
    rag_candidate_pool: int = 20
    rag_rrf_k: int = 60
    rag_recency_half_life_days: int = 30
    rag_agentic_enabled: bool = True
    rag_journal_index_enabled: bool = True
    rag_content_hash_enabled: bool = True
    rag_partial_refresh_enabled: bool = True
    rag_embedding_version: int = 1
    rag_embedding_model_filing: str = ""
    rag_temporal_filter_enabled: bool = True
    rag_router_enabled: bool = True
    chat_history_turns: int = 6
    rag_eval_enabled: bool = True
    rag_eval_interval_hours: int = 24
    rag_embedding_migration_enabled: bool = True
    sec_filings_enabled: bool = True
    sec_edgar_enabled: bool = True
    sec_edgar_user_agent: str = "TradeGuard-AI tradeguard@example.com"
    regime_detection_enabled: bool = True
    ml_retrain_min_trades: int = 10
    ml_model_type: str = "xgboost"
    ml_walk_forward_folds: int = 4
    ml_min_samples: int = 30
    ml_min_auc_delta: float = 0.02
    ml_retrain_interval_days: int = 7
    ml_low_confidence_threshold: float = 0.15
    ml_bullish_buy_min: float = 0.45
    ml_bullish_sell_max: float = 0.65
    ml_journal_retrain_enabled: bool = True
    ml_max_history_versions: int = 5
    ml_volatility_enabled: bool = True
    ml_vol_high_threshold: float = 0.55
    ml_vol_score_penalty: float = 12.0
    market_refresh_interval_minutes: int = 15

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
    def effective_robinhood_mcp_url(self) -> str:
        return (self.robinhood_mcp_url or self.robinhood_mcp_default_url).rstrip("/")

    @property
    def robinhood_oauth_redirect_uri(self) -> str:
        base = (self.api_public_url or "http://localhost:8000").rstrip("/")
        return f"{base}/api/brokers/robinhood/callback"

    @property
    def frontend_onboarding_url(self) -> str:
        if self.frontend_url.strip():
            return f"{self.frontend_url.rstrip('/')}/onboarding"
        if self.cors_origins:
            return f"{self.cors_origins[0].rstrip('/')}/onboarding"
        return "http://localhost:3000/onboarding"

    @property
    def use_slack_alerts(self) -> bool:
        if self.alert_provider == "mock":
            return False
        if self.alert_provider == "slack":
            return bool(self.slack_webhook_url)
        return bool(self.slack_webhook_url)

    @property
    def use_email_alerts(self) -> bool:
        if self.alert_provider == "mock":
            return False
        if self.alert_provider == "email":
            return bool(self.smtp_host and self.alert_email_to)
        return bool(self.smtp_host and self.alert_email_to)

    @property
    def active_alert_provider(self) -> str:
        channels: list[str] = []
        if self.use_slack_alerts:
            channels.append("slack")
        if self.use_email_alerts:
            channels.append("email")
        if not channels:
            return "mock"
        if len(channels) == 1:
            return channels[0]
        return "+".join(channels)

    @property
    def auth_enabled(self) -> bool:
        if self.auth_provider == "disabled":
            return False
        if self.auth_provider == "clerk":
            return bool(self.clerk_secret_key and self.clerk_jwt_issuer)
        return bool(self.clerk_secret_key and self.clerk_jwt_issuer)

    @property
    def platform_admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.platform_admin_emails.split(",") if e.strip()}

    @property
    def active_news_provider(self) -> str:
        mode = self.news_provider.lower()
        if mode == "mock":
            return "mock"
        if mode == "tavily" and self.tavily_api_key:
            return "tavily"
        if mode == "polygon" and self.polygon_api_key:
            return "polygon"
        if mode == "auto":
            if self.tavily_api_key:
                return "tavily"
            if self.polygon_api_key:
                return "polygon"
        return "mock"


settings = Settings()
