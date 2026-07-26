"""Plugin manager — discovery, lifecycle, health, and provider bridging."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.bridge import bridge_plugins_to_providers
from app.plugins.configuration import PluginConfigurationService
from app.plugins.dependency_resolver import PluginDependencyResolver
from app.plugins.health import PluginHealthService
from app.plugins.installer import PluginInstaller
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
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry, get_plugin_registry, reset_plugin_registry
from app.providers.composite_messaging import CompositeMessagingProvider
from app.providers.registry import ProviderRegistry, get_registry
from app.providers.services import ProviderService

logger = logging.getLogger(__name__)

_manager: PluginManager | None = None


class PluginManager:
    def __init__(
        self,
        registry: PluginRegistry | None = None,
        loader: PluginLoader | None = None,
    ) -> None:
        self.registry = registry or get_plugin_registry()
        self.loader = loader or PluginLoader()
        self.installer = PluginInstaller()
        self.dependencies = PluginDependencyResolver()
        self.health_service = PluginHealthService()
        self._started = False

    def discover_and_install(self) -> list[str]:
        installed: list[str] = []
        for plugin in self.loader.discover():
            manifest_errors = PluginLoader.validate_manifest(plugin.manifest)
            if manifest_errors:
                logger.error(
                    "Skipping invalid plugin manifest",
                    extra={"plugin": plugin.manifest.plugin_name, "errors": manifest_errors},
                )
                continue
            self.installer.install(self.registry, plugin)
            installed.append(plugin.manifest.plugin_name)
        return installed

    def startup(self, provider_registry: ProviderRegistry | None = None) -> None:
        if self._started:
            return
        plugins = {name: self.registry.get(name) for name in self.registry.list_all()}
        dep_errors = self.dependencies.validate_dependencies(plugins)
        perm_errors = self.dependencies.validate_permissions(plugins)
        if dep_errors or perm_errors:
            raise RuntimeError(f"Plugin startup failed: {dep_errors + perm_errors}")

        order = self.dependencies.resolve_install_order(plugins)
        for name in order:
            plugin = plugins[name]
            config_errors = PluginConfigurationService(plugin.manifest).validate_against_schema()
            plugin_errors = plugin.validate_configuration()
            if config_errors or plugin_errors:
                logger.warning(
                    "Plugin configuration incomplete — may run unconfigured",
                    extra={"plugin": name, "errors": config_errors + plugin_errors},
                )
            if self.registry.is_enabled(name):
                plugin.on_startup()

        reg = provider_registry or get_registry()
        bridge_plugins_to_providers(self.registry, reg)
        self._register_core_composite_providers(reg)
        self._started = True
        logger.info(
            "Plugin manager startup complete",
            extra={"plugins": self.registry.list_enabled()},
        )

    def shutdown(self) -> None:
        for name in reversed(self.registry.list_enabled()):
            self.registry.get(name).on_shutdown()
        self._started = False

    def reload_plugin(self, name: str, provider_registry: ProviderRegistry | None = None) -> None:
        self.registry.get(name).on_shutdown()
        module_plugins = [p for p in self.loader.discover() if p.manifest.plugin_name == name]
        if not module_plugins:
            raise KeyError(f"Plugin '{name}' not found on disk")
        self.installer.install(self.registry, module_plugins[0])
        self.registry.enable(name)
        reg = provider_registry or get_registry()
        bridge_plugins_to_providers(self.registry, reg)
        self.registry.get(name).on_startup()

    def health_check(self) -> dict[str, Any]:
        enabled = {name: self.registry.get(name) for name in self.registry.list_enabled()}
        return self.health_service.check_all(enabled)

    def admin_snapshot(self) -> dict[str, Any]:
        return {
            "installed": self.registry.discover_manifests(),
            "enabled": self.registry.list_enabled(),
            "health": self.health_check(),
            "configurations": [
                PluginConfigurationService(self.registry.get(name).manifest).snapshot()
                for name in self.registry.list_all()
            ],
        }

    @staticmethod
    def _register_core_composite_providers(reg: ProviderRegistry) -> None:
        """Core platform adapters — not vendor plugins."""
        if "composite" not in reg.list_registered(ProviderService.MESSAGING):
            reg.register(ProviderService.MESSAGING, CompositeMessagingProvider())

    # Typed accessors — business services use capabilities, not plugin names
    def get_telephony_plugin(self) -> TelephonyPlugin | None:
        return self.registry.first_of(TelephonyPlugin)

    def get_messaging_plugin(self) -> MessagingPlugin | None:
        return self.registry.first_of(MessagingPlugin)

    def get_voice_plugin(self) -> VoicePlugin | None:
        return self.registry.first_of(VoicePlugin)

    def get_storage_plugin(self) -> StoragePlugin | None:
        return self.registry.first_of(StoragePlugin)

    def get_payment_plugin(self) -> PaymentPlugin | None:
        return self.registry.first_of(PaymentPlugin)

    def get_speech_to_text_plugin(self) -> SpeechToTextPlugin | None:
        return self.registry.first_of(SpeechToTextPlugin)

    def get_email_plugin(self) -> EmailPlugin | None:
        return self.registry.first_of(EmailPlugin)

    def get_crm_plugin(self) -> CRMPlugin | None:
        return self.registry.first_of(CRMPlugin)

    def get_calendar_plugin(self) -> CalendarPlugin | None:
        return self.registry.first_of(CalendarPlugin)


def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


def bootstrap_plugins(
    *,
    provider_registry: ProviderRegistry | None = None,
    reset: bool = False,
) -> PluginManager:
    global _manager
    if reset:
        reset_plugin_registry()
    manager = PluginManager(registry=get_plugin_registry())
    manager.discover_and_install()
    manager.startup(provider_registry=provider_registry)
    _manager = manager
    return manager
