"""Unified messaging port — SMS, email, WhatsApp."""

from __future__ import annotations

from abc import abstractmethod

from app.providers.base import BaseProvider, ProviderResult


class MessagingProvider(BaseProvider):
    @abstractmethod
    def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        ...

    @abstractmethod
    def send_email(self, *, to: str, subject: str, body: str) -> ProviderResult:
        ...

    @abstractmethod
    def send_whatsapp(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        ...
