"""Alert provider interface."""

from abc import ABC, abstractmethod


class AlertProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def send(self, title: str, detail: str, severity: str, event_type: str) -> dict:
        pass
