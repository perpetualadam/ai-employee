"""VoIP.ms integration adapters — SMS URL callbacks and SIP-oriented voice control."""

from __future__ import annotations

import logging

from fastapi import Request

from app.config import get_settings
from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter

logger = logging.getLogger(__name__)


class VoipMsVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "voipms"

    def is_configured(self) -> bool:
        from app.voice import voipms_client

        return voipms_client.is_voipms_configured()

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("VoIP.ms is not configured")
        from app.voice import voipms_client

        settings = get_settings()
        did = call_id if call_id.isdigit() else (settings.voipms_did or settings.voipms_phone_number)
        routing = settings.voipms_routing or f"trg:{to_number}"
        voipms_client.set_did_routing(str(did), routing)
        logger.info("VoIP.ms DID routing updated for transfer", extra={"did": did, "to": to_number})


class VoipMsVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "voipms"

    async def parse_request(self, request: Request) -> dict[str, str]:
        # VoIP.ms voice is SIP-based; normalize any query/form fields for shared handlers.
        params: dict[str, str] = {k: str(v) for k, v in request.query_params.items()}
        if request.method.upper() == "POST":
            form = await request.form()
            params.update({k: str(v) for k, v in form.items()})
        if params.get("from") and not params.get("From"):
            params["From"] = params["from"]
        if params.get("to") and not params.get("To"):
            params["To"] = params["to"]
        return params


class VoipMsSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "voipms"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        params = {k: str(v) for k, v in request.query_params.items()}
        if request.method.upper() == "POST":
            form = await request.form()
            params.update({k: str(v) for k, v in form.items()})
        text = (params.get("message") or params.get("text") or params.get("Body") or "").strip()
        from_number = params.get("from") or params.get("From") or ""
        to_number = params.get("to") or params.get("To") or ""
        if not text and not from_number:
            return None
        return {"from": from_number, "to": to_number, "text": text}
