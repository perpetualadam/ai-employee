"""Twilio SMS outbound stub."""

from __future__ import annotations

from app.config import get_settings
from app.providers.capability_presets import runtime_caps, twilio_telephony
from app.services.messaging.provider import SmsProvider


class TwilioSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.twilio_account_sid and settings.twilio_auth_token)

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
        return {
            "sent": True,
            "provider": self.provider_name,
            "phone": to_number,
            "message": text,
            "id": "sms-twilio-stub",
        }
