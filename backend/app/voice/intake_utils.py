"""Backward-compatible re-exports — prefer app.domain.intake."""

from app.domain.intake import (
    extract_spoken_name,
    is_valid_customer_name,
    is_valid_service_address,
    normalize_caller_speech,
)

__all__ = [
    "extract_spoken_name",
    "is_valid_customer_name",
    "is_valid_service_address",
    "normalize_caller_speech",
]
