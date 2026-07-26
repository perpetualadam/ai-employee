"""Composite messaging adapter — delegates SMS and email to configured providers."""

from __future__ import annotations

from app.integrations.registry import get_email_provider, get_sms_provider
from app.providers.base import ProviderResult
from app.providers.capabilities import Capability, ProviderCapabilities
from app.providers.capability_presets import composite_messaging, runtime_caps
from app.providers.exceptions import CapabilityNotSupportedError
from app.providers.messaging import MessagingProvider


class CompositeMessagingProvider(MessagingProvider):
    """Unifies outbound SMS (telephony) and email without coupling business logic."""

    @property
    def provider_name(self) -> str:
        return "composite"

    def is_configured(self) -> bool:
        return get_sms_provider().is_configured() or get_email_provider().is_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(composite_messaging(), self, service="messaging")

    def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        sms = get_sms_provider()
        result = sms.send_sms(from_number, to_number, text)
        return ProviderResult(
            provider=sms.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    def send_email(self, *, to: str, subject: str, body: str) -> ProviderResult:
        email = get_email_provider()
        result = email.send_email(to, subject, body)
        return ProviderResult(
            provider=email.provider_name,
            external_id=result.get("id"),
            data=result,
        )

    def send_whatsapp(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        from app.providers.registry import get_registry
        from app.providers.services import ProviderService

        provider = get_registry().select(
            ProviderService.MESSAGING,
            required_capabilities=[Capability.WHATSAPP],
            require_healthy=True,
        )
        return provider.send_whatsapp(from_number=from_number, to_number=to_number, text=text)
