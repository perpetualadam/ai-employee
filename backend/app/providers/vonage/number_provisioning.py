"""Vonage number provisioning stub."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, vonage_numbers
from app.providers.number_provisioning import NumberProvisioningProvider
from app.providers.stub import StubProviderMixin, stub_result


class VonageNumberProvisioningProvider(StubProviderMixin, NumberProvisioningProvider):
    _credential_fields = ("vonage_api_key", "vonage_api_secret")

    @property
    def provider_name(self) -> str:
        return "vonage"

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(vonage_numbers(), self, service="numbers")

    def search_numbers(
        self,
        country_code: str,
        *,
        prefix: str | None = None,
        limit: int = 10,
        number_type: str | None = None,
    ) -> list[dict[str, Any]]:
        self._require_configured()
        return [{"phone_number": "+442071112233", "region": "Stub", "cost": "0.00"}]

    def purchase_number(self, phone_number: str) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, f"order-{phone_number}")

    def wait_for_purchase(self, order_id: str, *, timeout_seconds: int = 45) -> ProviderResult:
        return stub_result(self.provider_name, order_id, status="success")

    def find_number_record(self, phone_number: str) -> dict[str, Any] | None:
        if not self.is_configured():
            return None
        return {"id": f"pn-vonage-{phone_number}", "phone_number": phone_number}

    def release_number(self, provider_number_id: str) -> ProviderResult:
        return stub_result(self.provider_name, provider_number_id)

    def assign_number(self, provider_number_id: str) -> ProviderResult:
        return stub_result(self.provider_name, provider_number_id)

    def configure_voice(self, provider_number_id: str) -> ProviderResult:
        return stub_result(self.provider_name, provider_number_id)

    def configure_sms(self, provider_number_id: str) -> ProviderResult:
        return stub_result(self.provider_name, provider_number_id)
