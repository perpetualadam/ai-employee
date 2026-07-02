"""SMS provider abstraction — swap Telnyx, Twilio, etc. without changing call flow."""

from abc import ABC, abstractmethod


class SmsProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        """Return dict with sent, provider, optional id/error."""
