"""SignalWire telephony adapter — Compatibility API / cXML."""

from __future__ import annotations

import logging
from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, signalwire_telephony
from app.providers.exceptions import ProviderUnavailableError
from app.providers.telephony import TelephonyProvider
from app.voice import signalwire_client

logger = logging.getLogger(__name__)


def _markup_from_webhook_response(webhook_response: dict[str, Any]) -> str:
    markup = webhook_response.get("markup") or webhook_response.get("texml") or ""
    if not markup:
        raise ValueError("webhook_response must include markup (or texml)")
    return str(markup)


class SignalWireTelephonyProvider(TelephonyProvider):
    @property
    def provider_name(self) -> str:
        return "signalwire"

    def is_configured(self) -> bool:
        return signalwire_client.is_signalwire_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(signalwire_telephony(), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        markup = _markup_from_webhook_response(webhook_response)
        signalwire_client.update_call_cxml(call_id, markup)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        if not signalwire_client.is_outbound_call_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        result = signalwire_client.initiate_call(from_number, to_number, webhook_url)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("call_control_id") or result.get("id"),
            data=result,
        )

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        from app.integrations.adapters.signalwire_adapters import SignalWireVoiceCallControl

        control = SignalWireVoiceCallControl()
        await control.transfer_call(call_id, to_number)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def end_call(self, call_id: str) -> ProviderResult:
        signalwire_client.end_call(call_id)
        logger.info("Call ended via SignalWire REST hangup", extra={"call_id": call_id})
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        result = signalwire_client.send_sms(from_number, to_number, text)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        from_number = str(payload.get("From") or payload.get("from") or "").strip()
        to_number = str(payload.get("To") or payload.get("to") or "").strip()
        text = str(payload.get("Body") or payload.get("text") or "").strip()
        if not from_number and not text:
            return None
        return {"from": from_number, "to": to_number, "text": text}
