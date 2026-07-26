"""Plugin install / enable lifecycle."""

from __future__ import annotations

import logging

from app.plugins.interfaces import BasePlugin
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginInstaller:
    def install(self, registry: PluginRegistry, plugin: BasePlugin) -> None:
        errors = plugin.validate_configuration()
        if errors:
            logger.warning(
                "Plugin installed with configuration warnings",
                extra={"plugin": plugin.manifest.plugin_name, "errors": errors},
            )
        plugin.on_install()
        registry.register(plugin)
        logger.info("Plugin installed", extra={"plugin": plugin.manifest.plugin_name})

    def uninstall(self, registry: PluginRegistry, name: str) -> None:
        plugin = registry.get(name)
        registry.disable(name)
        plugin.on_shutdown()
        logger.info("Plugin uninstalled", extra={"plugin": name})
