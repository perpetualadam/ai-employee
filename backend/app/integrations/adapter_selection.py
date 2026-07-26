"""Select configured integration adapters using provider config and failover chains."""

from __future__ import annotations

from functools import lru_cache
from typing import Callable, TypeVar

from app.integrations.provider_resolution import adapter_failover_chain
from app.providers.services import ProviderService

T = TypeVar("T")


def select_adapter(
    registry: dict[str, Callable[[], T]],
    service: ProviderService,
    primary: str,
    *,
    fallbacks: list[str] | None = None,
) -> T:
    """
    Walk the configured failover chain and return the first configured adapter.

    Falls back to the primary adapter instance when none report configured — callers
    may raise when invoking operations on an unconfigured provider.
    """
    chain = adapter_failover_chain(service, primary)
    for name in fallbacks or []:
        if name not in chain:
            chain.append(name)

    for name in chain:
        factory = registry.get(name)
        if factory is None:
            continue
        instance = factory()
        if getattr(instance, "is_configured", lambda: True)():
            return instance

    factory = registry.get(primary.lower()) or registry.get(chain[0])
    if factory is None:
        raise KeyError(
            f"No adapter registered for service '{service.value}' "
            f"(primary={primary}, chain={chain})",
        )
    return factory()


def cached_adapter_factory(name: str, cls: type[T]) -> Callable[[], T]:
    """Build an LRU-cached zero-arg factory for a single adapter class."""

    @lru_cache
    def _factory() -> T:
        return cls()

    _factory.__name__ = f"adapter_{name}"
    return _factory
