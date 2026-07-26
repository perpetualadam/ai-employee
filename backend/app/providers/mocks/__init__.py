"""Mock provider implementations for tests and local development."""

from __future__ import annotations

from typing import Any, AsyncIterator

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import mock_all, runtime_caps
from app.providers.messaging import MessagingProvider
from app.providers.number_provisioning import NumberProvisioningProvider
from app.providers.regulatory import RegulatoryProvider
from app.providers.telephony import TelephonyProvider
from app.providers.voice import TranscriptSegment, VoiceProvider


class MockNumberProvisioningProvider(NumberProvisioningProvider):
    def __init__(self, name: str = "mock") -> None:
        self._name = name
        self.numbers: dict[str, dict[str, Any]] = {}

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(mock_all(self._name), self, service="numbers")

    def search_numbers(
        self,
        country_code: str,
        *,
        prefix: str | None = None,
        limit: int = 10,
        number_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return [{"phone_number": "+15551234567", "region": "Mock", "cost": "0.00"}]

    def purchase_number(self, phone_number: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=f"order-{phone_number}")

    def wait_for_purchase(self, order_id: str, *, timeout_seconds: int = 45) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=order_id, data={"status": "success"})

    def find_number_record(self, phone_number: str) -> dict[str, Any] | None:
        if phone_number not in self.numbers:
            self.numbers[phone_number] = {"id": f"pn-{phone_number}", "phone_number": phone_number}
        return self.numbers[phone_number]

    def release_number(self, provider_number_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=provider_number_id)

    def assign_number(self, provider_number_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=provider_number_id)

    def configure_voice(self, provider_number_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=provider_number_id)

    def configure_sms(self, provider_number_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=provider_number_id)


class MockRegulatoryProvider(RegulatoryProvider):
    def __init__(self, name: str = "mock") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(mock_all(self._name), self, service="regulatory")

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=f"eu-{business_id}")

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=f"doc-{filename}")

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=f"bundle-{country_code}")

    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=bundle_id)

    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=bundle_id, data={"status": "approved"})

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=bundle_id, data={"status": "approved"})

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=end_user_id, data={"status": "approved"})


class MockMessagingProvider(MessagingProvider):
    def __init__(self, name: str = "mock") -> None:
        self._name = name
        self.sent: list[dict[str, str]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(mock_all(self._name), self, service="messaging")

    def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        self.sent.append({"from": from_number, "to": to_number, "text": text})
        return ProviderResult(provider=self.provider_name, external_id="sms-mock-1")

    def send_email(self, *, to: str, subject: str, body: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id="email-mock-1")

    def send_whatsapp(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        return self.send_sms(from_number=from_number, to_number=to_number, text=text)


class MockTelephonyProvider(TelephonyProvider):
    def __init__(self, name: str = "mock", *, configured: bool = True) -> None:
        self._name = name
        self._configured = configured

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return self._configured

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(mock_all(self._name), self, service="telephony")

    async def answer_call(self, call_id: str, webhook_response: dict[str, Any]) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def outbound_call(
        self,
        *,
        from_number: str,
        to_number: str,
        webhook_url: str,
    ) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id="call-mock-1")

    async def transfer_call(self, call_id: str, to_number: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def end_call(self, call_id: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id=call_id)

    async def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        return ProviderResult(provider=self.provider_name, external_id="sms-mock-1")

    async def receive_sms(self, payload: dict[str, Any]) -> dict[str, str] | None:
        return {"from": "+1", "to": "+2", "text": "mock"}


class MockVoiceProvider(VoiceProvider):
    def __init__(self, name: str = "mock") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(mock_all(self._name), self, service="voice")

    async def speech_to_text(self, audio_bytes: bytes, *, language: str = "en") -> str:
        return "mock transcript"

    async def text_to_speech(self, text: str, *, voice: str = "alloy") -> bytes:
        return b"mock-audio"

    async def realtime_stream(
        self, audio_stream: AsyncIterator[bytes], *, language: str = "en"
    ) -> AsyncIterator[TranscriptSegment]:
        yield TranscriptSegment(text="mock", is_final=True)


from app.providers.mocks.storage import MockStorageProvider

__all__ = [
    "MockMessagingProvider",
    "MockNumberProvisioningProvider",
    "MockRegulatoryProvider",
    "MockStorageProvider",
    "MockTelephonyProvider",
    "MockVoiceProvider",
]
