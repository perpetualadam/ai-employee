"""Business-level provider override validation."""

from __future__ import annotations

from app.providers.services import ProviderService

PROVIDER_CONFIG_KEYS = frozenset(service.value for service in ProviderService)


def merge_provider_config(
    existing: dict[str, str] | None,
    updates: dict[str, str] | None,
    *,
    registered: dict[str, list[str]],
) -> dict[str, str]:
    """
    Merge provider overrides onto a business.

    Use empty string or ``auto`` in *updates* to remove an override for that service.
    """
    merged: dict[str, str] = dict(existing or {})
    if not updates:
        return merged

    for key, raw_value in updates.items():
        if key not in PROVIDER_CONFIG_KEYS:
            raise ValueError(f"Unknown provider service '{key}'")

        value = (raw_value or "").strip().lower()
        if value in ("", "auto", "default"):
            merged.pop(key, None)
            continue

        allowed = registered.get(key, [])
        if value not in allowed:
            allowed_label = ", ".join(sorted(allowed)) or "none"
            raise ValueError(
                f"Provider '{value}' is not registered for '{key}' (allowed: {allowed_label})",
            )
        merged[key] = value

    return merged
