"""Plugin port interfaces — business services depend on these, never vendor SDKs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.plugins.manifest import PluginManifest
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.voice.provider import TranscriptChunk


class BasePlugin(ABC):
    """Lifecycle hooks and capability advertisement for every plugin."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        ...

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    def on_install(self) -> None:
        """Called when plugin is first installed."""

    def on_enable(self) -> None:
        """Called when plugin is enabled."""

    def on_disable(self) -> None:
        """Called when plugin is disabled."""

    def on_startup(self) -> None:
        """Called during application startup after registration."""

    def on_shutdown(self) -> None:
        """Called during application shutdown."""

    def validate_configuration(self) -> list[str]:
        """Return list of configuration errors (empty when valid)."""
        return []

    def health(self) -> dict[str, Any]:
        caps = self.get_capabilities()
        return {
            "status": caps.health_status,
            "version": caps.provider_version,
            "latency_ms": caps.metadata.get("latency_ms"),
            "configured": self.is_configured(),
            "capabilities": caps.to_dict(),
            "supported_regions": sorted(caps.country_support),
            "supported_features": sorted(caps.supported_features()),
        }

    def register_providers(self, registry: Any) -> None:
        """Register port implementations with the provider registry."""

    def register_integrations(self) -> None:
        """Register legacy integration adapters (webhooks, SMS inbound)."""


class TelephonyPlugin(BasePlugin):
    @abstractmethod
    def get_telephony_provider(self) -> BaseProvider:
        ...

    @abstractmethod
    def get_number_provider(self) -> BaseProvider | None:
        ...

    @abstractmethod
    def get_regulatory_provider(self) -> BaseProvider | None:
        ...


class MessagingPlugin(BasePlugin):
    @abstractmethod
    def get_messaging_provider(self) -> BaseProvider | None:
        ...


class VoicePlugin(BasePlugin):
    @abstractmethod
    def get_voice_provider(self) -> BaseProvider:
        ...


class SpeechToTextPlugin(BasePlugin):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, *, language: str = "en") -> str:
        ...

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        *,
        language: str = "en-US",
    ) -> AsyncIterator[TranscriptChunk]:
        ...


class EmailPlugin(BasePlugin):
    @abstractmethod
    def send_email(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        ...


class PaymentPlugin(BasePlugin):
    @abstractmethod
    def is_payment_configured(self) -> bool:
        ...

    @abstractmethod
    def create_customer(
        self,
        *,
        email: str,
        name: str,
        metadata: dict[str, str],
    ) -> str:
        """Create or return a payment-provider customer id."""

    @abstractmethod
    def create_checkout_session(
        self,
        *,
        customer_id: str,
        plan_tier: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> str:
        """Return hosted checkout URL for a subscription plan."""

    @abstractmethod
    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        """Return hosted billing portal URL."""

    @abstractmethod
    def construct_webhook_event(self, payload: bytes, signature: str) -> dict:
        """Verify webhook signature and return parsed event payload."""


class StoragePlugin(BasePlugin):
    @abstractmethod
    def get_storage_provider(self) -> BaseProvider:
        ...


class CRMPlugin(BasePlugin):
    @abstractmethod
    def sync_customer(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class CalendarPlugin(BasePlugin):
    @abstractmethod
    def create_event(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        ...
