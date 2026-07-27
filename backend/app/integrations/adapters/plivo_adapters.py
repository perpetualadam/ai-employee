"""Plivo integration adapters — voice control, webhooks, and inbound SMS."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter
from app.voice.plivo_webhook_auth import validate_plivo_signature_v2

logger = logging.getLogger(__name__)


class PlivoVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "plivo"

    def is_configured(self) -> bool:
        from app.voice import plivo_client

        return plivo_client.is_plivo_configured()

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("Plivo voice is not configured")
        from app.voice import plivo_client
        from app.voice.voice_markup import PlivoVoiceMarkup

        xml = PlivoVoiceMarkup().build_transfer(to_number)
        plivo_client.update_call_xml(call_id, xml)
        logger.info("Plivo transfer initiated", extra={"call_id": call_id, "to": to_number})


class PlivoVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "plivo"

    async def parse_request(self, request: Request) -> dict[str, str]:
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}
        # Normalize Plivo CallUUID → CallSid for shared gather handlers.
        if params.get("CallUUID") and not params.get("CallSid"):
            params["CallSid"] = params["CallUUID"]
        if params.get("Speech") and not params.get("SpeechResult"):
            params["SpeechResult"] = params["Speech"]
        settings = get_settings()
        signature = request.headers.get("X-Plivo-Signature-V2") or request.headers.get(
            "X-Plivo-Signature-V3",
            "",
        )
        nonce = request.headers.get("X-Plivo-Signature-V2-Nonce") or request.headers.get(
            "X-Plivo-Signature-V3-Nonce",
            "",
        )
        if settings.plivo_auth_token and signature:
            # Strip query string for V2 base URI comparison when needed.
            uri = str(request.url).split("?", 1)[0]
            v3_header = bool(request.headers.get("X-Plivo-Signature-V3"))
            if not nonce:
                # Signature present without nonce cannot be verified — reject forged requests.
                if not settings.debug:
                    logger.warning(
                        "Plivo webhook signature missing nonce",
                        extra={"path": request.url.path},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid webhook signature",
                    )
            elif not validate_plivo_signature_v2(
                uri,
                nonce,
                signature,
                settings.plivo_auth_token,
            ):
                # V3 uses a different construction; accept when the V3 header is present
                # (no local V3 verifier yet). Reject failed V2-only signatures in prod.
                if not v3_header and not settings.debug:
                    logger.warning("Invalid Plivo webhook signature", extra={"path": request.url.path})
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid webhook signature",
                    )
        elif not settings.debug and not settings.plivo_auth_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Plivo is not configured",
            )
        return params


class PlivoSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "plivo"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        form = await request.form()
        if not form:
            return None
        params = {k: str(v) for k, v in form.items()}
        text = (params.get("Text") or params.get("Body") or "").strip()
        from_number = params.get("From", "")
        to_number = params.get("To", "")
        if not text and not from_number:
            return None
        return {"from": from_number, "to": to_number, "text": text}
