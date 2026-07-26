"""Resend email plugin."""

from __future__ import annotations

from typing import Any

from app.plugins.interfaces import EmailPlugin, MessagingPlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import resend_email, runtime_caps
from app.providers.registry import ProviderRegistry
from app.providers.resend.email import ResendEmailProvider
from app.providers.services import ProviderService
from plugins.resend.manifest import MANIFEST


class ResendPlugin(MessagingPlugin, EmailPlugin):
    def __init__(self) -> None:
        self._email = ResendEmailProvider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(resend_email(), self._email, service="messaging")

    def is_configured(self) -> bool:
        return self._email.is_configured()

    def get_messaging_provider(self) -> BaseProvider:
        return self._email

    def send_email(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        result = self._email.send_email(to=to, subject=subject, body=body)
        return {"sent": True, "provider": result.provider, "id": result.external_id, **result.data}

    def register_providers(self, registry: ProviderRegistry) -> None:
        registry.register(ProviderService.MESSAGING, self._email)


def create_plugin() -> ResendPlugin:
    return ResendPlugin()
