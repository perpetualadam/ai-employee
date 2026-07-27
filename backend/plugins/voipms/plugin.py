"""VoIP.ms telephony plugin."""

from __future__ import annotations

from app.integrations.registry import register_sms_inbound, register_voice_control, register_voice_webhook
from app.plugins.interfaces import TelephonyPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, voipms_telephony
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from app.providers.voipms.number_provisioning import VoipMsNumberProvisioningProvider
from app.providers.voipms.regulatory import VoipMsRegulatoryProvider
from app.providers.voipms.telephony import VoipMsTelephonyProvider
from plugins.voipms.manifest import MANIFEST


class VoipMsPlugin(TelephonyPlugin):
    def __init__(self) -> None:
        self._telephony = VoipMsTelephonyProvider()
        self._numbers = VoipMsNumberProvisioningProvider()
        self._regulatory = VoipMsRegulatoryProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(voipms_telephony(), self._telephony, service="telephony")

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
        from app.integrations.adapters.voipms_adapters import (
            VoipMsSmsInboundAdapter,
            VoipMsVoiceCallControl,
            VoipMsVoiceWebhookAdapter,
        )
        from app.integrations.adapters.voipms_duplex import VoipMsDuplexMediaAdapter
        from app.integrations.registry import register_duplex_adapter
        from app.services.messaging.factory import register_sms_outbound
        from app.services.messaging.voipms_sms import VoipMsSmsProvider

        register_voice_control("voipms", VoipMsVoiceCallControl)
        register_voice_webhook("voipms", VoipMsVoiceWebhookAdapter)
        register_sms_inbound("voipms", VoipMsSmsInboundAdapter)
        register_sms_outbound("voipms", VoipMsSmsProvider)
        register_duplex_adapter("voipms", VoipMsDuplexMediaAdapter)


def create_plugin() -> VoipMsPlugin:
    return VoipMsPlugin()
