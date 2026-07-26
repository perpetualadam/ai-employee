"""Telnyx plugin implementation."""

from __future__ import annotations

from typing import Any

from app.integrations.registry import register_sms_inbound, register_voice_control, register_voice_webhook
from app.plugins.interfaces import TelephonyPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, telnyx_telephony
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from plugins.telnyx.config import TelnyxPluginConfig
from plugins.telnyx.manifest import MANIFEST
from plugins.telnyx.services import number_provider, regulatory_provider, telephony_provider


class TelnyxPlugin(TelephonyPlugin):
    def __init__(self) -> None:
        self._config = TelnyxPluginConfig()
        self._telephony = telephony_provider()
        self._numbers = number_provider()
        self._regulatory = regulatory_provider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(telnyx_telephony(), self._telephony, service="telephony")

    def is_configured(self) -> bool:
        return self._telephony.is_configured()

    def get_telephony_provider(self) -> BaseProvider:
        return self._telephony

    def get_number_provider(self) -> BaseProvider:
        return self._numbers

    def get_regulatory_provider(self) -> BaseProvider:
        return self._regulatory

    def register_providers(self, registry: ProviderRegistry) -> None:
        registry.register(ProviderService.TELEPHONY, self._telephony)
        registry.register(ProviderService.NUMBERS, self._numbers)
        registry.register(ProviderService.REGULATORY, self._regulatory)

    def register_integrations(self) -> None:
        from app.integrations.adapters.telnyx_sms_inbound import TelnyxSmsInboundAdapter
        from app.integrations.adapters.telnyx_duplex import TelnyxDuplexMediaAdapter
        from app.integrations.adapters.telnyx_voice import TelnyxVoiceCallControl
        from app.integrations.adapters.telnyx_webhooks import TelnyxVoiceWebhookAdapter
        from app.integrations.registry import register_duplex_adapter
        from app.services.messaging.factory import register_sms_outbound
        from app.services.messaging.telnyx_sms import TelnyxSmsProvider

        register_voice_control("telnyx", TelnyxVoiceCallControl)
        register_voice_webhook("telnyx", TelnyxVoiceWebhookAdapter)
        register_sms_inbound("telnyx", TelnyxSmsInboundAdapter)
        register_sms_outbound("telnyx", TelnyxSmsProvider)
        register_duplex_adapter("telnyx", TelnyxDuplexMediaAdapter)

    def health(self) -> dict[str, Any]:
        data = super().health()
        data["latency_ms"] = self._telephony.latency_ms()
        return data


def create_plugin() -> TelnyxPlugin:
    return TelnyxPlugin()
