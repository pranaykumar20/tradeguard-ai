"""SMTP email alert provider."""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.core.config import settings
from app.providers.alerts.base import AlertProvider
from app.providers.alerts.mock import MockAlertProvider

logger = structlog.get_logger()

SEVERITY_LABEL = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}


class EmailAlertProvider(AlertProvider):
    provider_name = "email"

    def __init__(self):
        self._fallback = MockAlertProvider()

    def _configured(self) -> bool:
        return bool(
            settings.smtp_host
            and settings.alert_email_to
            and (settings.smtp_user or settings.smtp_port != 587)
        )

    def _send_sync(self, title: str, detail: str, severity: str, event_type: str) -> None:
        label = SEVERITY_LABEL.get(severity, severity.upper())
        body = (
            f"TradeGuard AI Alert\n\n"
            f"Title: {title}\n"
            f"Severity: {label}\n"
            f"Type: {event_type}\n\n"
            f"{detail}\n"
        )
        msg = MIMEMultipart()
        msg["Subject"] = f"[TradeGuard {label}] {title}"
        msg["From"] = settings.alert_email_from or settings.smtp_user or settings.alert_email_to
        msg["To"] = settings.alert_email_to
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            if settings.smtp_port in (587, 2587):
                server.starttls()
                server.ehlo()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

    async def send(self, title: str, detail: str, severity: str, event_type: str) -> dict:
        if not settings.smtp_host or not settings.alert_email_to:
            return await self._fallback.send(title, detail, severity, event_type)

        try:
            await asyncio.to_thread(self._send_sync, title, detail, severity, event_type)
            return {
                "status": "sent",
                "provider": self.provider_name,
                "title": title,
                "severity": severity,
                "event_type": event_type,
            }
        except Exception as exc:
            logger.error("email_alert_failed", error=str(exc), title=title)
            return await self._fallback.send(title, detail, severity, event_type)
