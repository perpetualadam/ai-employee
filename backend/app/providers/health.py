"""Provider health reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    service: str
    healthy: bool
    status: str
    latency_ms: float | None = None
    version: str = "1.0.0"
    details: dict[str, Any] = field(default_factory=dict)
