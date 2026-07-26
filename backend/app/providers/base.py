"""Shared provider types."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.providers.capabilities import ProviderCapabilities
from app.providers.health import ProviderHealth


@dataclass(frozen=True)
class ProviderResult:
    """Normalized success payload from any provider."""

    provider: str
    data: dict[str, Any] = field(default_factory=dict)
    external_id: str | None = None


class BaseProvider(ABC):
    """All providers expose a stable name, configuration probe, and health signals."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Self-describing capability advertisement — queried by selection engine."""

    def provider_version(self) -> str:
        return self.version()

    def supported_countries(self) -> list[str]:
        return sorted(self.get_capabilities().country_support)

    def supported_number_types(self) -> list[str]:
        return sorted(self.get_capabilities().supported_number_types)

    def supported_features(self) -> frozenset[str]:
        return self.get_capabilities().supported_features()

    def version(self) -> str:
        return "1.0.0"

    def latency_ms(self) -> float | None:
        """Optional live probe — subclasses may override with a real ping."""
        return None

    def status(self) -> str:
        if not self.is_configured():
            return "unconfigured"
        return "ok"

    def health(self, *, service: str = "unknown") -> ProviderHealth:
        start = time.perf_counter()
        configured = self.is_configured()
        latency = self.latency_ms()
        if latency is None and configured:
            latency = round((time.perf_counter() - start) * 1000, 2)
        return ProviderHealth(
            provider=self.provider_name,
            service=service,
            healthy=configured and self.status() == "ok",
            status=self.status(),
            latency_ms=latency,
            version=self.version(),
            details={"configured": configured},
        )
