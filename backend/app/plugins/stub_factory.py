"""Factory for marketplace-ready stub plugins."""

from __future__ import annotations

from app.plugins.categories import PluginCategory
from app.plugins.interfaces import BasePlugin
from app.plugins.manifest import PluginManifest
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import mock_all, runtime_caps


def build_stub_plugin(
    *,
    name: str,
    category: PluginCategory,
    description: str,
    author: str = "AI Employee",
    services: tuple[str, ...] = (),
    permissions: tuple[str, ...] = (),
    enabled_by_default: bool = False,
    priority: int = 50,
) -> BasePlugin:
    manifest = PluginManifest(
        plugin_name=name,
        plugin_version="0.1.0",
        plugin_author=author,
        plugin_description=description,
        plugin_category=category,
        supported_services=services,
        permissions=permissions,
        enabled_by_default=enabled_by_default,
        provider_priority=priority,
    )

    class _StubPlugin(BasePlugin):
        @property
        def manifest(self) -> PluginManifest:
            return manifest

        def get_capabilities(self) -> ProviderCapabilities:
            return runtime_caps(mock_all(name), self, service=category.value)

        def is_configured(self) -> bool:
            return False

    return _StubPlugin()
