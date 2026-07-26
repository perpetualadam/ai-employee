"""Resolve provider context for a business — country, overrides, active number owner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Business


def resolve_provider_context(
    business: Business,
    db: Session | None,
    *,
    resource_provider: str | None = None,
) -> tuple[str, dict[str, str]]:
    """
    Returns (country_code, business_overrides).

    When an active phone number exists, its ``provider`` becomes the telephony/messaging
    resource owner unless explicitly overridden on the business.
    """
    overrides: dict[str, str] = dict(getattr(business, "provider_config", None) or {})

    if db is not None and resource_provider is None:
        from app.repositories.phone_number_repository import PhoneNumberRepository

        active = PhoneNumberRepository(db).get_active_for_business(business.id)
        if active and active.provider:
            overrides.setdefault("telephony", active.provider)
            overrides.setdefault("messaging", active.provider)
            overrides.setdefault("numbers", active.provider)

    if resource_provider:
        overrides.setdefault("telephony", resource_provider)

    return business.country, overrides
