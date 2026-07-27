"""Telnyx telephony adapter — wraps existing telnyx_client without leaking to services."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, telnyx_telephony
from app.providers.exceptions import ProviderUnavailableError
from app.providers.telephony import TelephonyProvider
from app.voice import telnyx_client

logger = logging.getLogger(__name__)


class TelnyxTelephonyProvider(TelephonyProvider):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        return telnyx_client.is_telnyx_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(telnyx_telephony(), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        texml = webhook_response.get("markup") or webhook_response.get("texml") or ""
        if not texml:
            raise ValueError("webhook_response must include markup (or texml)")
        telnyx_client.update_call_texml(call_id, str(texml))
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        if not telnyx_client.is_outbound_call_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        result = telnyx_client.initiate_call(from_number, to_number, webhook_url)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("call_control_id") or result.get("id"),
            data=result,
        )

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        from app.integrations.adapters.telnyx_voice import TelnyxVoiceCallControl

        control = TelnyxVoiceCallControl()
        await control.transfer_call(call_id, to_number)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def end_call(self, call_id: str) -> ProviderResult:
        settings = get_settings()
        hangup_texml = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
        telnyx_client.update_call_texml(call_id, hangup_texml)
        logger.info("Call ended via TeXML hangup", extra={"call_id": call_id, "account": settings.telnyx_account_sid})
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        result = telnyx_client.send_sms(from_number, to_number, text)
        return ProviderResult(
            provider=self.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        from app.voice.messaging_webhook import parse_telnyx_sms_payload

        return parse_telnyx_sms_payload(payload)
