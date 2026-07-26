"""Number provisioning port — search, purchase, configure numbers."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from app.providers.base import BaseProvider, ProviderResult


class NumberProvisioningProvider(BaseProvider):
    @abstractmethod
    def search_numbers(
        self,
        country_code: str,
        *,
        prefix: str | None = None,
        limit: int = 10,
        number_type: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def purchase_number(self, phone_number: str) -> ProviderResult:
        ...

    @abstractmethod
    def wait_for_purchase(self, order_id: str, *, timeout_seconds: int = 45) -> ProviderResult:
        ...

    @abstractmethod
    def find_number_record(self, phone_number: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def release_number(self, provider_number_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def assign_number(self, provider_number_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def configure_voice(self, provider_number_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def configure_sms(self, provider_number_id: str) -> ProviderResult:
        ...
