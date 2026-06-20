"""Alert provider factory."""

from app.core.config import settings
from app.providers.alerts.base import AlertProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.alerts.slack import SlackAlertProvider

_provider: AlertProvider | None = None


def get_alert_provider() -> AlertProvider:
    global _provider
    if _provider is None:
        if settings.use_slack_alerts:
            _provider = SlackAlertProvider()
        else:
            _provider = MockAlertProvider()
    return _provider
