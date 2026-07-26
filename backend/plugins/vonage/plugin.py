"""Vonage telephony plugin."""

from __future__ import annotations

from app.integrations.registry import register_sms_inbound, register_voice_control, register_voice_webhook
from app.plugins.interfaces import TelephonyPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, vonage_telephony
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from app.providers.vonage.number_provisioning import VonageNumberProvisioningProvider
from app.providers.vonage.regulatory import VonageRegulatoryProvider
from app.providers.vonage.telephony import VonageTelephonyProvider
from plugins.vonage.manifest import MANIFEST


class VonagePlugin(TelephonyPlugin):
    def __init__(self) -> None:
        self._telephony = VonageTelephonyProvider()
        self._numbers = VonageNumberProvisioningProvider()
        self._regulatory = VonageRegulatoryProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(vonage_telephony(), self._telephony, service="telephony")

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
        from app.integrations.adapters.vonage_stubs import (
            VonageSmsInboundAdapter,
            VonageVoiceCallControl,
            VonageVoiceWebhookAdapter,
        )
        from app.services.messaging.factory import register_sms_outbound
        from app.services.messaging.vonage_sms import VonageSmsProvider

        register_voice_control("vonage", VonageVoiceCallControl)
        register_voice_webhook("vonage", VonageVoiceWebhookAdapter)
        register_sms_inbound("vonage", VonageSmsInboundAdapter)
        register_sms_outbound("vonage", VonageSmsProvider)


def create_plugin() -> VonagePlugin:
    return VonagePlugin()
