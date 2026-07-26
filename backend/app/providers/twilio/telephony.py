"""Twilio telephony stub — register and configure via TWILIO_* env vars."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, twilio_telephony
from app.providers.stub import StubProviderMixin, stub_result
from app.providers.telephony import TelephonyProvider


class TwilioTelephonyProvider(StubProviderMixin, TelephonyProvider):
    _credential_fields = ("twilio_account_sid", "twilio_auth_token")

    @property
    def provider_name(self) -> str:
        return "twilio"

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(twilio_telephony(), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        self._require_configured()
        markup = webhook_response.get("texml", "")
        if not markup:
            raise ValueError("webhook_response must include texml")
        from app.voice import twilio_client

        twilio_client.update_call_twiml(call_id, markup)
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, "call-twilio-stub")

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, call_id)

    async def end_call(self, call_id: str) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, call_id)

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, "sms-twilio-stub")

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        return {"from": "+1", "to": "+2", "text": "twilio-stub"}
