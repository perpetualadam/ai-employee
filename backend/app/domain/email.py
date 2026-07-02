"""Email validation helpers."""

from __future__ import annotations


def is_plausible_email(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    cleaned = value.strip()
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        return False
    local, _, domain = cleaned.partition("@")
    if not local or not domain or "." not in domain:
        return False
    return True
