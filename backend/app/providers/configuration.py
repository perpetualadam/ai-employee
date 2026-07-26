"""Data-driven provider configuration — loaded from JSON, overridable per business."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.telecom import normalize_country_code, resolve_region_code
from app.providers.services import ProviderService

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "provider_defaults.json"


@lru_cache
def load_provider_configuration() -> dict[str, Any]:
    if not _CONFIG_PATH.is_file():
        logger.warning("Provider config missing at %s — using empty defaults", _CONFIG_PATH)
        return {"defaults": {}, "countries": {}, "failover": {}}
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def reload_provider_configuration() -> dict[str, Any]:
    load_provider_configuration.cache_clear()
    return load_provider_configuration()


class ProviderConfiguration:
    """Resolves provider names from config files and optional business overrides."""

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        self._raw = raw if raw is not None else load_provider_configuration()

    @property
    def defaults(self) -> dict[str, str]:
        return dict(self._raw.get("defaults") or {})

    @property
    def countries(self) -> dict[str, dict[str, str]]:
        return dict(self._raw.get("countries") or {})

    @property
    def failover(self) -> dict[str, list[str]]:
        return dict(self._raw.get("failover") or {})

    @property
    def priority(self) -> dict[str, dict[str, list[str]]]:
        return dict(self._raw.get("priority") or {})

    @property
    def weights(self) -> dict[str, int]:
        return dict(self._raw.get("weights") or {})

    def resolve(
        self,
        service: ProviderService,
        *,
        country: str | None = None,
        business_overrides: dict[str, str] | None = None,
        resource_provider: str | None = None,
    ) -> str:
        """
        Resolution order:
        1. Explicit resource provider (e.g. phone number already on Twilio)
        2. Business override for this service
        3. Country-specific config (with EU region fallback)
        4. Global defaults
        """
        service_key = service.value

        if resource_provider:
            return resource_provider.lower()

        if business_overrides and service_key in business_overrides:
            return business_overrides[service_key].lower()

        if country:
            code = normalize_country_code(country)
            region = resolve_region_code(country)
            country_map = self.countries.get(code) or self.countries.get(region) or {}
            if service_key in country_map:
                return country_map[service_key].lower()

        default = self.defaults.get(service_key)
        if default:
            return default.lower()

        raise KeyError(f"No provider configured for service '{service_key}'")

    def failover_chain(self, service: ProviderService, primary: str) -> list[str]:
        chain = list(self.failover.get(service.value) or [])
        primary_lower = primary.lower()
        ordered: list[str] = []
        for name in [primary_lower, *chain]:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def priority_chain(
        self,
        service: ProviderService,
        country: str | None,
        primary: str,
    ) -> list[str]:
        """Country priority list — primary first, then configured fallbacks."""
        from app.domain.telecom import normalize_country_code, resolve_region_code

        service_key = service.value
        country_chains = self.priority
        candidates: list[str] = []

        if country:
            code = normalize_country_code(country)
            region = resolve_region_code(country)
            for key in (code, region):
                service_map = country_chains.get(key) or {}
                candidates.extend(service_map.get(service_key) or [])

        ordered: list[str] = []
        for name in [primary.lower(), *candidates, *self.failover_chain(service, primary)]:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def provider_weight(self, provider_name: str) -> int:
        return int(self.weights.get(provider_name.lower(), 100))


@lru_cache
def get_provider_configuration() -> ProviderConfiguration:
    return ProviderConfiguration()
