"""Stripe SDK adapter — all vendor imports live in the plugin layer."""

from __future__ import annotations

import stripe

from app.plugins.exceptions import PaymentWebhookVerificationError
from plugins.stripe.config import StripePluginConfig


class StripePaymentService:
    def __init__(self, config: StripePluginConfig | None = None) -> None:
        self._config = config or StripePluginConfig()

    def _configure(self) -> None:
        stripe.api_key = self._config.require_secret_key()

    def create_customer(self, *, email: str, name: str, metadata: dict[str, str]) -> str:
        self._configure()
        customer = stripe.Customer.create(email=email, name=name, metadata=metadata)
        return customer.id

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> str:
        self._configure()
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            subscription_data={"metadata": metadata},
        )
        if not session.url:
            raise RuntimeError("Stripe checkout session did not return a URL")
        return session.url

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        self._configure()
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        if not session.url:
            raise RuntimeError("Stripe portal session did not return a URL")
        return session.url

    def construct_webhook_event(self, payload: bytes, signature: str) -> dict:
        self._configure()
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self._config.require_webhook_secret(),
            )
        except stripe.SignatureVerificationError as exc:
            raise PaymentWebhookVerificationError(str(exc)) from exc
        return dict(event)
