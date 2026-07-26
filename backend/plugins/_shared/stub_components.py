"""Reusable building blocks for marketplace stub plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.plugins.categories import PluginCategory
from app.plugins.interfaces import BasePlugin
from app.plugins.manifest import PluginManifest
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import mock_all, runtime_caps


@dataclass(frozen=True)
class StubPluginMetadata:
    """Plugin-local metadata record — isolated from core business data."""

    plugin_name: str
    installed: bool = True
    configured: bool = False


class StubPluginConfig:
    """Isolated configuration accessor for stub plugins."""

    def __init__(self, env_prefix: str) -> None:
        self._env_prefix = env_prefix.upper()

    def snapshot(self) -> dict[str, Any]:
        return {"env_prefix": self._env_prefix, "configured": False}

    def validate(self) -> list[str]:
        return []


class StubPluginHealth:
    @staticmethod
    def check(plugin: BasePlugin) -> dict[str, Any]:
        return {
            **plugin.health(),
            "latency_ms": None,
            "marketplace_stub": True,
        }


class StubPluginDependencies:
    REQUIRES: tuple[str, ...] = ()


def build_stub_manifest(
    *,
    name: str,
    category: PluginCategory,
    description: str,
    services: tuple[str, ...] = (),
    permissions: tuple[str, ...] = (),
) -> PluginManifest:
    return PluginManifest(
        plugin_name=name,
        plugin_version="0.1.0",
        plugin_author="AI Employee",
        plugin_description=description,
        plugin_category=category,
        supported_services=services,
        permissions=permissions,
        enabled_by_default=False,
        provider_priority=50,
    )


def build_stub_plugin_class(manifest: PluginManifest) -> type[BasePlugin]:
    class _StubPlugin(BasePlugin):
        @property
        def manifest(self) -> PluginManifest:
            return manifest

        def get_capabilities(self) -> ProviderCapabilities:
            return runtime_caps(mock_all(manifest.plugin_name), self, service=manifest.plugin_category.value)

        def is_configured(self) -> bool:
            return False

    _StubPlugin.__name__ = f"{manifest.plugin_name.title()}Plugin"
    return _StubPlugin
