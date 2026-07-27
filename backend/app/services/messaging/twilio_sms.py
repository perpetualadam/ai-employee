"""Twilio SMS outbound adapter — parity with TelnyxSmsProvider."""

from __future__ import annotations

from app.config import get_settings
from app.providers.capability_presets import runtime_caps, twilio_telephony
from app.services.messaging.provider import SmsProvider
from app.voice import twilio_client


class TwilioSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        return twilio_client.is_twilio_configured()

    def get_capabilities(self):
        return runtime_caps(twilio_telephony(), self, service="messaging")

    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        if not self.is_configured():
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "Twilio is not configured",
            }
        settings = get_settings()
        sender = from_number or settings.twilio_phone_number
        if not sender and not settings.twilio_messaging_service_sid:
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "Twilio sender number or messaging service is not configured",
            }
        try:
            result = twilio_client.send_sms(sender or "", to_number, text)
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
