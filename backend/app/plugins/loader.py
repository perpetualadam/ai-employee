"""Dynamic plugin discovery from backend/plugins/."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

from app.plugins.interfaces import BasePlugin
from app.plugins.manifest import CORE_VERSION, PluginManifest

logger = logging.getLogger(__name__)

PLUGINS_ROOT = Path(__file__).resolve().parents[2] / "plugins"


class PluginLoader:
    """Discover and import plugin packages from the plugins directory."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or PLUGINS_ROOT

    def discover(self) -> list[BasePlugin]:
        plugins: list[BasePlugin] = []
        if not self._root.is_dir():
            logger.warning("Plugins directory missing: %s", self._root)
            return plugins

        for entry in sorted(self._root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            plugin_module = entry / "plugin.py"
            if not plugin_module.is_file():
                continue
            plugin = self._load_plugin(entry.name)
            if plugin is not None:
                plugins.append(plugin)
        return plugins

    def _load_plugin(self, package_name: str) -> BasePlugin | None:
        module_name = f"plugins.{package_name}.plugin"
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.exception("Failed to import plugin module", extra={"plugin": package_name})
            return None

        factory = getattr(module, "create_plugin", None)
        if callable(factory):
            plugin = factory()
            if isinstance(plugin, BasePlugin):
                return plugin

        plugin_cls = getattr(module, "Plugin", None)
        if plugin_cls is not None and issubclass(plugin_cls, BasePlugin):
            return plugin_cls()

        logger.error("Plugin module has no create_plugin() or Plugin class", extra={"plugin": package_name})
        return None

    @staticmethod
    def validate_manifest(manifest: PluginManifest) -> list[str]:
        errors: list[str] = []
        if not manifest.plugin_name:
            errors.append("plugin_name is required")
        if manifest.minimum_core_version > CORE_VERSION:
            errors.append(
                f"Plugin requires core {manifest.minimum_core_version}, running {CORE_VERSION}",
            )
        return errors
