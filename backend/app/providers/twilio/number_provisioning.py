"""Twilio number provisioning adapter — parity with TelnyxNumberProvisioningProvider."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, twilio_numbers
from app.providers.exceptions import ProviderTimeoutError, ProviderUnavailableError
from app.providers.number_provisioning import NumberProvisioningProvider
from app.voice import twilio_client


class TwilioNumberProvisioningProvider(NumberProvisioningProvider):
    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        return twilio_client.is_phone_provisioning_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(twilio_numbers(), self, service="numbers")

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
        return twilio_client.search_available_phone_numbers(
            country_code,
            prefix=prefix,
            limit=limit,
            number_type=number_type,
        )

    def purchase_number(self, phone_number: str) -> ProviderResult:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        order = twilio_client.create_number_order(phone_number)
        return ProviderResult(
            provider=self.provider_name,
            external_id=order.get("id"),
            data=order,
        )

    def wait_for_purchase(self, order_id: str, *, timeout_seconds: int = 45) -> ProviderResult:
        try:
            order = twilio_client.wait_for_number_order(order_id, timeout_seconds=timeout_seconds)
        except TimeoutError as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        return ProviderResult(provider=self.provider_name, external_id=order_id, data=order)

    def find_number_record(self, phone_number: str) -> dict[str, Any] | None:
        return twilio_client.find_phone_number_record(phone_number)

    def release_number(self, provider_number_id: str) -> ProviderResult:
        if not twilio_client.is_twilio_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        twilio_client.release_phone_number(provider_number_id)
        return ProviderResult(provider=self.provider_name, external_id=provider_number_id)

    def assign_number(self, provider_number_id: str) -> ProviderResult:
        return self.configure_voice(provider_number_id)

    def configure_voice(self, provider_number_id: str) -> ProviderResult:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        settings = get_settings()
        voice_url = f"{settings.public_api_url.rstrip('/')}/api/v1/voice/inbound"
        result = twilio_client.configure_phone_number(
            provider_number_id,
            voice_url=voice_url,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=provider_number_id,
            data=result,
        )

    def configure_sms(self, provider_number_id: str) -> ProviderResult:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        settings = get_settings()
        sms_url = f"{settings.public_api_url.rstrip('/')}/api/v1/sms/inbound"
        result = twilio_client.configure_phone_number(
            provider_number_id,
            sms_url=sms_url,
            messaging_service_sid=settings.twilio_messaging_service_sid or None,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=provider_number_id,
            data=result,
        )
