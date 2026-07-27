"""Plivo telephony adapter — parity with TelnyxTelephonyProvider."""

from __future__ import annotations

import logging
from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, plivo_telephony
from app.providers.exceptions import ProviderUnavailableError
from app.providers.telephony import TelephonyProvider
from app.voice import plivo_client

logger = logging.getLogger(__name__)


def _markup_from_webhook_response(webhook_response: dict[str, Any]) -> str:
    markup = webhook_response.get("markup") or webhook_response.get("texml") or ""
    if not markup:
        raise ValueError("webhook_response must include markup (or texml)")
    return str(markup)


class PlivoTelephonyProvider(TelephonyProvider):
    @property
    def provider_name(self) -> str:
        return "plivo"

    def is_configured(self) -> bool:
        return plivo_client.is_plivo_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(plivo_telephony(), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        markup = _markup_from_webhook_response(webhook_response)
        plivo_client.update_call_xml(call_id, markup)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        if not plivo_client.is_outbound_call_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        result = plivo_client.initiate_call(from_number, to_number, webhook_url)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("call_control_id") or result.get("id"),
            data=result,
        )

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        from app.integrations.adapters.plivo_adapters import PlivoVoiceCallControl

        control = PlivoVoiceCallControl()
        await control.transfer_call(call_id, to_number)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def end_call(self, call_id: str) -> ProviderResult:
        plivo_client.end_call(call_id)
        logger.info("Call ended via Plivo REST hangup", extra={"call_id": call_id})
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        result = plivo_client.send_sms(from_number, to_number, text)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        from_number = str(payload.get("From") or payload.get("from") or "").strip()
        to_number = str(payload.get("To") or payload.get("to") or "").strip()
        text = str(payload.get("Text") or payload.get("text") or payload.get("Body") or "").strip()
        if not from_number and not text:
            return None
        return {"from": from_number, "to": to_number, "text": text}
