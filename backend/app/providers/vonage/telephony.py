"""Vonage telephony adapter — parity with TelnyxTelephonyProvider."""

from __future__ import annotations

import logging
from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, vonage_telephony
from app.providers.exceptions import ProviderUnavailableError
from app.providers.telephony import TelephonyProvider
from app.voice import vonage_client

logger = logging.getLogger(__name__)


def _markup_from_webhook_response(webhook_response: dict[str, Any]) -> str:
    markup = webhook_response.get("markup") or webhook_response.get("texml") or ""
    if not markup:
        raise ValueError("webhook_response must include markup (or texml)")
    return str(markup)


class VonageTelephonyProvider(TelephonyProvider):
    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        return vonage_client.is_vonage_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(vonage_telephony(), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        markup = _markup_from_webhook_response(webhook_response)
        vonage_client.update_call_ncco(call_id, markup)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        if not vonage_client.is_outbound_call_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        result = vonage_client.initiate_call(from_number, to_number, webhook_url)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("call_control_id") or result.get("id"),
            data=result,
        )

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        from app.integrations.adapters.vonage_stubs import VonageVoiceCallControl

        control = VonageVoiceCallControl()
        await control.transfer_call(call_id, to_number)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def end_call(self, call_id: str) -> ProviderResult:
        vonage_client.end_call(call_id)
        logger.info("Call ended via Vonage REST hangup", extra={"call_id": call_id})
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        result = vonage_client.send_sms(from_number, to_number, text)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        text = payload.get("text") or ""
        if isinstance(payload.get("message"), dict):
            text = text or payload["message"].get("content", "")
        from_number = str(payload.get("from") or payload.get("msisdn") or "").strip()
        to_number = str(payload.get("to") or "").strip()
        text_str = str(text).strip()
        if not from_number and not text_str:
            return None
        return {"from": from_number, "to": to_number, "text": text_str}
