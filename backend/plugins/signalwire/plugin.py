"""SignalWire telephony plugin."""

from __future__ import annotations

from app.integrations.registry import register_sms_inbound, register_voice_control, register_voice_webhook
from app.plugins.interfaces import TelephonyPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, signalwire_telephony
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from app.providers.signalwire.number_provisioning import SignalWireNumberProvisioningProvider
from app.providers.signalwire.regulatory import SignalWireRegulatoryProvider
from app.providers.signalwire.telephony import SignalWireTelephonyProvider
from plugins.signalwire.manifest import MANIFEST


class SignalWirePlugin(TelephonyPlugin):
    def __init__(self) -> None:
        self._telephony = SignalWireTelephonyProvider()
        self._numbers = SignalWireNumberProvisioningProvider()
        self._regulatory = SignalWireRegulatoryProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(signalwire_telephony(), self._telephony, service="telephony")

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
        from app.integrations.adapters.signalwire_adapters import (
            SignalWireSmsInboundAdapter,
            SignalWireVoiceCallControl,
            SignalWireVoiceWebhookAdapter,
        )
        from app.integrations.adapters.signalwire_duplex import SignalWireDuplexMediaAdapter
        from app.integrations.registry import register_duplex_adapter
        from app.services.messaging.factory import register_sms_outbound
        from app.services.messaging.signalwire_sms import SignalWireSmsProvider

        register_voice_control("signalwire", SignalWireVoiceCallControl)
        register_voice_webhook("signalwire", SignalWireVoiceWebhookAdapter)
        register_sms_inbound("signalwire", SignalWireSmsInboundAdapter)
        register_sms_outbound("signalwire", SignalWireSmsProvider)
        register_duplex_adapter("signalwire", SignalWireDuplexMediaAdapter)


def create_plugin() -> SignalWirePlugin:
    return SignalWirePlugin()
