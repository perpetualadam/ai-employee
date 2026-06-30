"""Backward-compatible re-exports — prefer app.domain.phone."""

from app.domain.phone import is_plausible_phone, normalize_phone, resolve_caller_phone

__all__ = ["is_plausible_phone", "normalize_phone", "resolve_caller_phone"]
