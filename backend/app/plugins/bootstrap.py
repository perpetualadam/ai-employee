"""Plugin bootstrap entrypoint."""

from __future__ import annotations

from app.plugins.manager import bootstrap_plugins, get_plugin_manager
from app.providers.registry import get_registry


def ensure_plugins_loaded() -> None:
    manager = get_plugin_manager()
    if not manager.registry.list_all():
        bootstrap_plugins(provider_registry=get_registry())
