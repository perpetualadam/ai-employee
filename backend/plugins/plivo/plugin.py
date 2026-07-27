"""Plivo telephony plugin."""

from __future__ import annotations

from app.integrations.registry import register_sms_inbound, register_voice_control, register_voice_webhook
from app.plugins.interfaces import TelephonyPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import plivo_telephony, runtime_caps
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from app.providers.plivo.number_provisioning import PlivoNumberProvisioningProvider
from app.providers.plivo.regulatory import PlivoRegulatoryProvider
from app.providers.plivo.telephony import PlivoTelephonyProvider
from plugins.plivo.manifest import MANIFEST


class PlivoPlugin(TelephonyPlugin):
    def __init__(self) -> None:
        self._telephony = PlivoTelephonyProvider()
        self._numbers = PlivoNumberProvisioningProvider()
        self._regulatory = PlivoRegulatoryProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(plivo_telephony(), self._telephony, service="telephony")

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
        from app.integrations.adapters.plivo_adapters import (
            PlivoSmsInboundAdapter,
            PlivoVoiceCallControl,
            PlivoVoiceWebhookAdapter,
        )
        from app.integrations.adapters.plivo_duplex import PlivoDuplexMediaAdapter
        from app.integrations.registry import register_duplex_adapter
        from app.services.messaging.factory import register_sms_outbound
        from app.services.messaging.plivo_sms import PlivoSmsProvider

        register_voice_control("plivo", PlivoVoiceCallControl)
        register_voice_webhook("plivo", PlivoVoiceWebhookAdapter)
        register_sms_inbound("plivo", PlivoSmsInboundAdapter)
        register_sms_outbound("plivo", PlivoSmsProvider)
        register_duplex_adapter("plivo", PlivoDuplexMediaAdapter)


def create_plugin() -> PlivoPlugin:
    return PlivoPlugin()
