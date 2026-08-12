"""Integration contracts — ports for external systems (Hexagonal / ports-and-adapters)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


@dataclass(frozen=True)
class NormalizedRecordingEvent:
    """Provider-agnostic recording webhook payload."""

    status: str
    recording_url: str | None = None
    recording_id: str | None = None
    duration_seconds: int | None = None


class CallRecordingAdapter(ABC):
    """
    Inject provider-native call recording into answer markup and normalize
    recording-ready webhooks so storage/playback stays CPaaS-agnostic.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    def supports_inline_recording(self) -> bool:
        return True

    @abstractmethod
    def inject_recording(self, markup: str, *, base_url: str, call_log_id: str) -> str:
        ...

    @abstractmethod
    def normalize_webhook(self, params: dict[str, str]) -> NormalizedRecordingEvent:
        ...

    def download_recording(self, url: str) -> tuple[bytes, str]:
        """Fetch recording bytes. Override when the provider requires auth."""
        import httpx

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
            if not content_type.startswith("audio/"):
                content_type = "audio/mpeg"
            return response.content, content_type


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
