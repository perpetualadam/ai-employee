"""Call control facade — telephony operations via TelephonyProvider."""

from __future__ import annotations

import logging
from typing import Any

from app.providers.telephony import TelephonyProvider

logger = logging.getLogger(__name__)


class CallService:
    def __init__(self, telephony_provider: TelephonyProvider) -> None:
        self._telephony = telephony_provider

    async def answer_call(self, call_id: str, *, texml: str) -> dict:
        result = await self._telephony.answer_call(call_id, {"texml": texml})
        return {"call_id": result.external_id, "provider": result.provider}

    async def place_outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> dict:
        result = await self._telephony.outbound_call(
            from_number=from_number,
            to_number=to_number,
            webhook_url=webhook_url,
        )
        return {
            "call_id": result.external_id,
            "provider": result.provider,
            **result.data,
        }

    async def transfer_call(self, call_id: str, to_number: str) -> dict:
        result = await self._telephony.transfer_call(call_id, to_number)
        return {"call_id": result.external_id, "provider": result.provider}

    async def end_call(self, call_id: str) -> dict:
        result = await self._telephony.end_call(call_id)
        return {"call_id": result.external_id, "provider": result.provider}

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> dict:
        result = await self._telephony.send_sms(
            from_number=from_number,
            to_number=to_number,
            text=text,
        )
        return {"id": result.external_id, "provider": result.provider, **result.data}

    async def parse_inbound_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        return await self._telephony.receive_sms(payload)

    def is_configured(self) -> bool:
        return self._telephony.is_configured()

    @property
    def provider_name(self) -> str:
        return self._telephony.provider_name
