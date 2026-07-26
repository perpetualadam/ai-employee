"""Bootstrap plugins — replaces direct vendor imports in core bootstrap."""

from __future__ import annotations

import logging

from app.plugins.manager import bootstrap_plugins, get_plugin_manager
from app.providers.registry import ProviderRegistry, get_registry

logger = logging.getLogger(__name__)


def bootstrap_providers(registry: ProviderRegistry | None = None) -> ProviderRegistry:
    """Load plugins and bridge them into the provider registry."""
    reg = registry or get_registry()
    bootstrap_plugins(provider_registry=reg)
    return reg


def bootstrap_integration_adapters(registry: ProviderRegistry | None = None) -> None:
    """Register webhook and messaging adapters from enabled plugins."""
    manager = get_plugin_manager()
    if not manager.registry.list_all():
        bootstrap_plugins(provider_registry=registry or get_registry())
        return
    for name in manager.registry.list_enabled():
        manager.registry.get(name).register_integrations()


# Production bootstrap via plugin discovery
bootstrap_providers()
