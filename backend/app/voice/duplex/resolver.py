"""Resolve duplex media adapter from the tenant telephony provider — not hardcoded to Telnyx."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.integrations.registry import get_duplex_media_adapter as _get_from_registry

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Business
    from app.voice.duplex.contracts import DuplexMediaAdapter


def get_duplex_media_adapter(
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> DuplexMediaAdapter | None:
    """Return the configured duplex adapter for the business telephony CPaaS, if any."""
    try:
        adapter = _get_from_registry(business=business, db=db)
    except KeyError:
        return None
    if not adapter.supports_duplex():
        return None
    return adapter
