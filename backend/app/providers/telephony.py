"""Telephony provider port — call control without vendor coupling."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from app.providers.base import BaseProvider, ProviderResult


class TelephonyProvider(BaseProvider):
    @abstractmethod
    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        """Accept or respond to an inbound call (TeXML/TwiML payload)."""

    @abstractmethod
    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        """Place an outbound call."""

    @abstractmethod
    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        """Transfer an active call."""

    @abstractmethod
    async def end_call(self, call_id: str) -> ProviderResult:
        """Terminate an active call."""

    @abstractmethod
    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        """Send SMS via telephony carrier."""

    @abstractmethod
    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        """Normalize inbound SMS webhook payload."""
