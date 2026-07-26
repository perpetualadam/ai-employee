"""Stripe plugin configuration — isolated from core settings access patterns."""

from __future__ import annotations

from app.config import get_settings
from app.models.enums import PlanTier


class StripePluginConfig:
    @property
    def secret_key(self) -> str | None:
        return get_settings().stripe_secret_key

    @property
    def webhook_secret(self) -> str | None:
        return get_settings().stripe_webhook_secret

    def price_id_for_plan(self, plan: PlanTier | str) -> str:
        settings = get_settings()
        tier = plan.value if isinstance(plan, PlanTier) else plan
        if tier == PlanTier.PRO.value:
            if not settings.stripe_price_pro:
                raise ValueError("STRIPE_PRICE_PRO is not configured")
            return settings.stripe_price_pro
        if not settings.stripe_price_starter:
            raise ValueError("STRIPE_PRICE_STARTER is not configured")
        return settings.stripe_price_starter

    def require_secret_key(self) -> str:
        key = self.secret_key
        if not key:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured")
        return key

    def require_webhook_secret(self) -> str:
        secret = self.webhook_secret
        if not secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
        return secret
