"""Integration contracts — ports for external systems (Hexagonal / ports-and-adapters)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from fastapi import Request


class VoiceCallControl(ABC):
    """Outbound call control — transfer, TeXML push, etc."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def transfer_call(self, call_id: str, to_number: str) -> None:
        ...


class VoiceWebhookAdapter(ABC):
    """Verify and normalize voice CPaaS webhooks to flat param dicts."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def parse_request(self, request: Request) -> dict[str, str]:
        ...


class SmsInboundAdapter(ABC):
    """Verify and parse inbound SMS webhooks."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        ...


class EmailProvider(ABC):
    """Transactional email delivery."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> dict:
        ...


class SupportsProviderName(Protocol):
    provider_name: str

    def is_configured(self) -> bool: ...
