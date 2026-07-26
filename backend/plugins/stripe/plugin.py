"""Stripe payments plugin."""

from __future__ import annotations

from app.models.enums import PlanTier
from app.plugins.interfaces import PaymentPlugin
from app.providers.capabilities import ProviderCapabilities
from plugins.stripe.config import StripePluginConfig
from plugins.stripe.manifest import MANIFEST
from plugins.stripe.services import StripePaymentService


class StripePlugin(PaymentPlugin):
    def __init__(self) -> None:
        self._config = StripePluginConfig()
        self._service = StripePaymentService(self._config)

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="stripe",
            provider_version="1.0.0",
            country_support=frozenset({"*"}),
            metadata={"payments": True},
        )

    def is_configured(self) -> bool:
        return self.is_payment_configured()

    def is_payment_configured(self) -> bool:
        return bool(self._config.secret_key)

    def create_customer(
        self,
        *,
        email: str,
        name: str,
        metadata: dict[str, str],
    ) -> str:
        return self._service.create_customer(email=email, name=name, metadata=metadata)

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        plan_tier: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> str:
        price_id = self._config.price_id_for_plan(plan_tier)
        return self._service.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        return self._service.create_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )

    def construct_webhook_event(self, payload: bytes, signature: str) -> dict:
        return self._service.construct_webhook_event(payload, signature)


def create_plugin() -> StripePlugin:
    return StripePlugin()
