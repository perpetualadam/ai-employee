"""Telnyx plugin-local metadata models (future SDK response caches)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TelnyxNumberRecord:
    provider_number_id: str
    phone_number: str
