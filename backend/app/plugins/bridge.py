"""Bridge plugin implementations into the provider registry."""

from __future__ import annotations

import logging

from app.plugins.interfaces import BasePlugin, MessagingPlugin, StoragePlugin, TelephonyPlugin, VoicePlugin
from app.plugins.registry import PluginRegistry
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService

logger = logging.getLogger(__name__)


def bridge_plugins_to_providers(
    plugin_registry: PluginRegistry,
    provider_registry: ProviderRegistry,
) -> None:
    """Register provider ports from enabled plugins — core never imports vendors."""
    for name in plugin_registry.list_enabled():
        plugin = plugin_registry.get(name)
        plugin.register_providers(provider_registry)
        plugin.register_integrations()
        logger.debug("Bridged plugin", extra={"plugin": name})
