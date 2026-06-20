"""Slack webhook alert provider."""

import httpx
import structlog

from app.core.config import settings
from app.providers.alerts.base import AlertProvider
from app.providers.alerts.mock import MockAlertProvider

logger = structlog.get_logger()

SEVERITY_EMOJI = {
    "critical": ":rotating_light:",
    "high": ":warning:",
    "medium": ":large_yellow_circle:",
    "low": ":information_source:",
}


class SlackAlertProvider(AlertProvider):
    provider_name = "slack"

    def __init__(self):
        self._fallback = MockAlertProvider()

    async def send(self, title: str, detail: str, severity: str, event_type: str) -> dict:
        if not settings.slack_webhook_url:
            return await self._fallback.send(title, detail, severity, event_type)

        emoji = SEVERITY_EMOJI.get(severity, ":bell:")
        payload = {
            "text": f"{emoji} *TradeGuard — {title}*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{emoji} *{title}*\n"
                            f"*Severity:* {severity.upper()} · *Type:* `{event_type}`\n"
                            f"{detail}"
                        ),
                    },
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(settings.slack_webhook_url, json=payload)
                resp.raise_for_status()
            return {
                "status": "sent",
                "provider": self.provider_name,
                "title": title,
                "severity": severity,
                "event_type": event_type,
            }
        except Exception as exc:
            logger.error("slack_alert_failed", error=str(exc), title=title)
            return await self._fallback.send(title, detail, severity, event_type)
