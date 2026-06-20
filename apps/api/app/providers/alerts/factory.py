"""Alert provider factory — mock, Slack, email, or composite multi-channel."""

from app.core.config import settings
from app.providers.alerts.base import AlertProvider
from app.providers.alerts.composite import CompositeAlertProvider
from app.providers.alerts.email import EmailAlertProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.alerts.slack import SlackAlertProvider

_provider: AlertProvider | None = None


def get_alert_provider() -> AlertProvider:
    global _provider
    if _provider is None:
        providers: list[AlertProvider] = []
        if settings.use_slack_alerts:
            providers.append(SlackAlertProvider())
        if settings.use_email_alerts:
            providers.append(EmailAlertProvider())
        if not providers:
            _provider = MockAlertProvider()
        elif len(providers) == 1:
            _provider = providers[0]
        else:
            _provider = CompositeAlertProvider(providers)
    return _provider


def reset_alert_provider() -> None:
    """Reset cached provider (tests)."""
    global _provider
    _provider = None
