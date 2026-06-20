"""Mock alert provider — logs alerts locally (default when no Slack webhook)."""

import structlog

from app.providers.alerts.base import AlertProvider

logger = structlog.get_logger()


class MockAlertProvider(AlertProvider):
    provider_name = "mock"

    async def send(self, title: str, detail: str, severity: str, event_type: str) -> dict:
        logger.warning(
            "alert_mock",
            title=title,
            detail=detail,
            severity=severity,
            event_type=event_type,
        )
        return {
            "status": "sent",
            "provider": self.provider_name,
            "title": title,
            "severity": severity,
            "event_type": event_type,
        }
