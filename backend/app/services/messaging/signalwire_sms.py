"""SignalWire SMS outbound adapter."""

from __future__ import annotations

from app.config import get_settings
from app.providers.capability_presets import runtime_caps, signalwire_telephony
from app.services.messaging.provider import SmsProvider
from app.voice import signalwire_client


class SignalWireSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "signalwire"

    def is_configured(self) -> bool:
        return signalwire_client.is_signalwire_configured()

    def get_capabilities(self):
        return runtime_caps(signalwire_telephony(), self, service="messaging")

    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        if not self.is_configured():
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "SignalWire is not configured",
            }
        settings = get_settings()
        sender = from_number or settings.signalwire_phone_number
        if not sender:
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "SignalWire sender number is not configured",
            }
        try:
            result = signalwire_client.send_sms(sender, to_number, text)
            return {
                "sent": True,
                "provider": self.provider_name,
                "phone": to_number,
                "message": text,
                "id": result.get("id"),
            }
        except Exception as exc:
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": str(exc),
            }
