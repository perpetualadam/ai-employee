"""Channel-agnostic business rules (intake, phone, call state)."""

from app.domain.call import call_has_booking
from app.domain.intake import (
    extract_spoken_name,
    is_valid_customer_name,
    is_valid_service_address,
    normalize_caller_speech,
)
from app.domain.phone import is_plausible_phone, normalize_phone, resolve_caller_phone

__all__ = [
    "call_has_booking",
    "extract_spoken_name",
    "is_plausible_phone",
    "is_valid_customer_name",
    "is_valid_service_address",
    "normalize_caller_speech",
    "normalize_phone",
    "resolve_caller_phone",
]
