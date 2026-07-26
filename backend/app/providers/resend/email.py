"""Resend email adapter — implements email leg of MessagingProvider."""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import resend_email, runtime_caps
from app.providers.exceptions import ProviderUnavailableError
from app.providers.messaging import MessagingProvider

logger = logging.getLogger(__name__)


class ResendEmailProvider(MessagingProvider):
    """Email-only messaging adapter; SMS/WhatsApp raise until configured separately."""

    @property
    def provider_name(self) -> str:
        return "resend"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.resend_api_key and settings.resend_from_email)

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(resend_email(), self, service="messaging")

    def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        raise NotImplementedError("ResendEmailProvider does not send SMS — use a telephony SMS adapter")

    def send_email(self, *, to: str, subject: str, body: str) -> ProviderResult:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        settings = get_settings()
        payload = {
            "from": settings.resend_from_email,
            "to": [to],
            "subject": subject,
            "text": body,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        logger.info("Email sent via Resend", extra={"to": to, "id": data.get("id")})
        return ProviderResult(provider=self.provider_name, external_id=data.get("id"), data=data)

    def send_whatsapp(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        raise NotImplementedError("WhatsApp not implemented for Resend adapter")
