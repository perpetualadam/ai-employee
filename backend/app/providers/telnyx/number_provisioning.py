"""Telnyx number provisioning adapter."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, telnyx_numbers
from app.providers.exceptions import ProviderTimeoutError, ProviderUnavailableError
from app.providers.number_provisioning import NumberProvisioningProvider
from app.voice import telnyx_client


class TelnyxNumberProvisioningProvider(NumberProvisioningProvider):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        return telnyx_client.is_phone_provisioning_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(telnyx_numbers(), self, service="numbers")

    def search_numbers(
        self,
        country_code: str,
        *,
        prefix: str | None = None,
        limit: int = 10,
        number_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        return telnyx_client.search_available_phone_numbers(
            country_code,
            prefix=prefix,
            limit=limit,
            number_type=number_type,
        )

    def purchase_number(self, phone_number: str) -> ProviderResult:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        order = telnyx_client.create_number_order(phone_number)
        return ProviderResult(
            provider=self.provider_name,
            external_id=order.get("id"),
            data=order,
        )

    def wait_for_purchase(self, order_id: str, *, timeout_seconds: int = 45) -> ProviderResult:
        try:
            order = telnyx_client.wait_for_number_order(order_id, timeout_seconds=timeout_seconds)
        except TimeoutError as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        return ProviderResult(provider=self.provider_name, external_id=order_id, data=order)

    def find_number_record(self, phone_number: str) -> dict[str, Any] | None:
        return telnyx_client.find_phone_number_record(phone_number)

    def release_number(self, provider_number_id: str) -> ProviderResult:
        if not telnyx_client.is_telnyx_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        telnyx_client._request("DELETE", f"/phone_numbers/{provider_number_id}")
        return ProviderResult(provider=self.provider_name, external_id=provider_number_id)

    def assign_number(self, provider_number_id: str) -> ProviderResult:
        return self.configure_voice(provider_number_id)

    def configure_voice(self, provider_number_id: str) -> ProviderResult:
        settings = get_settings()
        if not settings.telnyx_texml_connection_id:
            raise ProviderUnavailableError(provider=self.provider_name)
        result = telnyx_client.configure_phone_number(
            provider_number_id,
            connection_id=settings.telnyx_texml_connection_id,
            messaging_profile_id=None,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=provider_number_id,
            data=result,
        )

    def configure_sms(self, provider_number_id: str) -> ProviderResult:
        settings = get_settings()
        if not telnyx_client.is_telnyx_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        if not settings.telnyx_messaging_profile_id:
            return ProviderResult(provider=self.provider_name, external_id=provider_number_id, data={})
        telnyx_client._request(
            "PATCH",
            f"/phone_numbers/{provider_number_id}/messaging",
            json={"messaging_profile_id": settings.telnyx_messaging_profile_id},
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=provider_number_id,
            data={"messaging_profile_id": settings.telnyx_messaging_profile_id},
        )
