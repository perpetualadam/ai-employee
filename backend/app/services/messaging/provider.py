"""SMS provider abstraction — swap CPaaS vendors without changing call flow."""

from abc import ABC, abstractmethod

from app.providers.capabilities import ProviderCapabilities


class SmsProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        ...

    @abstractmethod
    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        """Return dict with sent, provider, optional id/error."""
