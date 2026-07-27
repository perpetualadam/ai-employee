"""SignalWire Compatibility API adapters — cXML webhooks and call control."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter
from app.voice.twilio_webhook_auth import validate_twilio_signature

logger = logging.getLogger(__name__)


class SignalWireVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "signalwire"

    def is_configured(self) -> bool:
        from app.voice import signalwire_client

        return signalwire_client.is_signalwire_configured()

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("SignalWire voice is not configured")
        from app.voice import signalwire_client
        from app.voice.voice_markup import SignalWireVoiceMarkup

        cxml = SignalWireVoiceMarkup().build_transfer(to_number)
        signalwire_client.update_call_cxml(call_id, cxml)
        logger.info("SignalWire transfer initiated", extra={"call_id": call_id, "to": to_number})


class SignalWireVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "signalwire"

    async def parse_request(self, request: Request) -> dict[str, str]:
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}
        settings = get_settings()
        signature = request.headers.get("X-Twilio-Signature", "")
        token = settings.signalwire_api_token
        if token:
            url = str(request.url)
            if not validate_twilio_signature(url, params, signature, token):
                logger.warning("Invalid SignalWire webhook signature", extra={"path": request.url.path})
                if not settings.debug:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid webhook signature",
                    )
        elif not settings.debug:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SignalWire is not configured",
            )
        return params


class SignalWireSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "signalwire"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        form = await request.form()
        if not form:
            return None
        params = {k: str(v) for k, v in form.items()}
        settings = get_settings()
        signature = request.headers.get("X-Twilio-Signature", "")
        if settings.signalwire_api_token:
            url = str(request.url)
            if not validate_twilio_signature(url, params, signature, settings.signalwire_api_token):
                if not settings.debug:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid webhook signature",
                    )
        text = params.get("Body", "").strip()
        if not text and not params.get("From"):
            return None
        return {
            "from": params.get("From", ""),
            "to": params.get("To", ""),
            "text": text,
        }
