"""Resend transactional email adapter."""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.integrations.contracts import EmailProvider

logger = logging.getLogger(__name__)


class ResendEmailAdapter(EmailProvider):
    @property
    def provider_name(self) -> str:
        return "resend"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.resend_api_key and settings.resend_from_email)

    def send_email(self, to: str, subject: str, body: str) -> dict:
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
        return {"id": data.get("id"), "sent": True, "provider": self.provider_name}
