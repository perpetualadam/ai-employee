"""Twilio integration adapters — voice control, webhooks, and inbound SMS."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter
from app.voice.twilio_webhook_auth import validate_twilio_signature

logger = logging.getLogger(__name__)


class TwilioVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        from app.voice import twilio_client

        return twilio_client.is_twilio_configured()

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("Twilio voice is not configured")
        from app.voice import twilio_client
        from app.voice.voice_markup import TwilioVoiceMarkup

        twiml = TwilioVoiceMarkup().build_transfer(to_number)
        twilio_client.update_call_twiml(call_id, twiml)
        logger.info("Twilio transfer initiated", extra={"call_id": call_id, "to": to_number})


class TwilioVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "twilio"

    async def parse_request(self, request: Request) -> dict[str, str]:
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}
        settings = get_settings()
        signature = request.headers.get("X-Twilio-Signature", "")
        if settings.twilio_auth_token:
            url = str(request.url)
            if not validate_twilio_signature(url, params, signature, settings.twilio_auth_token):
                logger.warning("Invalid Twilio webhook signature", extra={"path": request.url.path})
                if not settings.debug:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid webhook signature",
                    )
        elif not settings.debug:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twilio is not configured",
            )
        return params


class TwilioSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "twilio"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        form = await request.form()
        if not form:
            return None
        params = {k: str(v) for k, v in form.items()}
        settings = get_settings()
        signature = request.headers.get("X-Twilio-Signature", "")
        if settings.twilio_auth_token:
            url = str(request.url)
            if not validate_twilio_signature(url, params, signature, settings.twilio_auth_token):
                logger.warning("Invalid Twilio SMS webhook signature", extra={"path": request.url.path})
                if not settings.debug:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid webhook signature",
                    )
        elif not settings.debug:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twilio is not configured",
            )
        text = params.get("Body", "").strip()
        if not text and not params.get("From"):
            return None
        return {
            "from": params.get("From", ""),
            "to": params.get("To", ""),
            "text": text,
        }
