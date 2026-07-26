"""Plugin registry — installed plugins indexed by category and capability."""

from __future__ import annotations

from typing import TypeVar

from app.plugins.categories import PluginCategory
from app.plugins.interfaces import (
    BasePlugin,
    CRMPlugin,
    CalendarPlugin,
    EmailPlugin,
    MessagingPlugin,
    PaymentPlugin,
    SpeechToTextPlugin,
    StoragePlugin,
    TelephonyPlugin,
    VoicePlugin,
)

T = TypeVar("T", bound=BasePlugin)


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}
        self._enabled: set[str] = set()

    def register(self, plugin: BasePlugin) -> None:
        name = plugin.manifest.plugin_name
        self._plugins[name] = plugin
        if plugin.manifest.enabled_by_default:
            self._enabled.add(name)

    def get(self, name: str) -> BasePlugin:
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        return self._plugins[name]

    def list_all(self) -> list[str]:
        return sorted(self._plugins.keys())

    def list_enabled(self) -> list[str]:
        return sorted(self._enabled)

    def is_enabled(self, name: str) -> bool:
        return name in self._enabled

    def enable(self, name: str) -> None:
        plugin = self.get(name)
        plugin.on_enable()
        self._enabled.add(name)

    def disable(self, name: str) -> None:
        plugin = self.get(name)
        plugin.on_disable()
        self._enabled.discard(name)

    def by_category(self, category: PluginCategory) -> list[BasePlugin]:
        return [
            plugin
            for plugin in self._plugins.values()
            if plugin.manifest.plugin_category == category and self.is_enabled(plugin.manifest.plugin_name)
        ]

    def get_typed(self, name: str, expected: type[T]) -> T:
        plugin = self.get(name)
        if not isinstance(plugin, expected):
            raise TypeError(f"Plugin '{name}' is not a {expected.__name__}")
        return plugin

    def first_of(
        self,
        expected: type[T],
        *,
        category: PluginCategory | None = None,
    ) -> T | None:
        for name in self.list_enabled():
            plugin = self._plugins[name]
            if category and plugin.manifest.plugin_category != category:
                continue
            if isinstance(plugin, expected) and plugin.is_configured():
                return plugin
        return None

    def discover_manifests(self) -> list[dict]:
        return [plugin.manifest.to_dict() for plugin in self._plugins.values()]


_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_plugin_registry() -> PluginRegistry:
    global _registry
    _registry = PluginRegistry()
    return _registry
