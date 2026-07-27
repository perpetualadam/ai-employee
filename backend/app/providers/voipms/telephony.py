"""VoIP.ms telephony adapter — SMS + SIP routing (no REST gather/XML)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, voipms_telephony
from app.providers.exceptions import ProviderUnavailableError
from app.providers.telephony import TelephonyProvider
from app.voice import voipms_client

logger = logging.getLogger(__name__)


class VoipMsTelephonyProvider(TelephonyProvider):
    @property
    def provider_name(self) -> str:
        return "voipms"

    def is_configured(self) -> bool:
        return voipms_client.is_voipms_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(voipms_telephony(), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        # VoIP.ms does not push live call XML; inbound voice is SIP-routed.
        del webhook_response
        logger.info("VoIP.ms answer_call acknowledged (SIP-routed)", extra={"call_id": call_id})
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        del from_number, to_number, webhook_url
        raise ProviderUnavailableError(
            "VoIP.ms does not expose REST outbound AI calls — use SIP/account dialing",
            provider=self.provider_name,
        )

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        settings = get_settings()
        did = call_id if call_id.isdigit() else (settings.voipms_did or settings.voipms_phone_number)
        if not did:
            raise ProviderUnavailableError(provider=self.provider_name)
        # Best-effort: route DID to a tel: target account pattern when routing configured.
        routing = settings.voipms_routing or f"trg:{to_number}"
        voipms_client.set_did_routing(did, routing)
        return ProviderResult(provider=self.provider_name, external_id=call_id, data={"to": to_number})

    async def end_call(self, call_id: str) -> ProviderResult:
        del call_id
        raise ProviderUnavailableError(
            "VoIP.ms does not expose REST hangup for SIP sessions",
            provider=self.provider_name,
        )

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        result = voipms_client.send_sms(from_number, to_number, text)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        from_number = str(payload.get("from") or payload.get("From") or "").strip()
        to_number = str(payload.get("to") or payload.get("To") or "").strip()
        text = str(payload.get("message") or payload.get("text") or payload.get("Body") or "").strip()
        if not from_number and not text:
            return None
        return {"from": from_number, "to": to_number, "text": text}
