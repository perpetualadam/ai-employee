"""Twilio telephony plugin."""

from __future__ import annotations

from app.integrations.registry import register_sms_inbound, register_voice_control, register_voice_webhook
from app.plugins.interfaces import TelephonyPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, twilio_telephony
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from app.providers.twilio.number_provisioning import TwilioNumberProvisioningProvider
from app.providers.twilio.regulatory import TwilioRegulatoryProvider
from app.providers.twilio.telephony import TwilioTelephonyProvider
from plugins.twilio.manifest import MANIFEST


class TwilioPlugin(TelephonyPlugin):
    def __init__(self) -> None:
        self._telephony = TwilioTelephonyProvider()
        self._numbers = TwilioNumberProvisioningProvider()
        self._regulatory = TwilioRegulatoryProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(twilio_telephony(), self._telephony, service="telephony")

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
        from app.integrations.adapters.twilio_stubs import (
            TwilioSmsInboundAdapter,
            TwilioVoiceCallControl,
            TwilioVoiceWebhookAdapter,
        )
        from app.services.messaging.factory import register_sms_outbound
        from app.services.messaging.twilio_sms import TwilioSmsProvider

        register_voice_control("twilio", TwilioVoiceCallControl)
        register_voice_webhook("twilio", TwilioVoiceWebhookAdapter)
        register_sms_inbound("twilio", TwilioSmsInboundAdapter)
        register_sms_outbound("twilio", TwilioSmsProvider)


def create_plugin() -> TwilioPlugin:
    return TwilioPlugin()
