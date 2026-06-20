"""Multi-channel alert dispatch — Slack + email when configured."""

from app.providers.alerts.base import AlertProvider


class CompositeAlertProvider(AlertProvider):
    provider_name = "composite"

    def __init__(self, providers: list[AlertProvider]):
        self._providers = providers

    async def send(self, title: str, detail: str, severity: str, event_type: str) -> dict:
        channels: list[str] = []
        for provider in self._providers:
            result = await provider.send(title, detail, severity, event_type)
            channels.append(result.get("provider", provider.provider_name))
        return {
            "status": "sent",
            "provider": self.provider_name,
            "channels": channels,
            "title": title,
            "severity": severity,
            "event_type": event_type,
        }
