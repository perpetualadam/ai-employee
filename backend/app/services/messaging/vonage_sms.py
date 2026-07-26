"""Vonage SMS outbound stub."""

from __future__ import annotations

from app.config import get_settings
from app.providers.capability_presets import runtime_caps, vonage_telephony
from app.services.messaging.provider import SmsProvider


class VonageSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.vonage_api_key and settings.vonage_api_secret)

    def get_capabilities(self):
        return runtime_caps(vonage_telephony(), self, service="messaging")

    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        if not self.is_configured():
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "Vonage is not configured",
            }
        return {
            "sent": True,
            "provider": self.provider_name,
            "phone": to_number,
            "message": text,
            "id": "sms-vonage-stub",
        }
