"""Local platform plugin — dev SMS/email and filesystem storage."""

from __future__ import annotations

from typing import Any

from app.plugins.interfaces import MessagingPlugin, StoragePlugin
from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import local_sms, local_storage, runtime_caps
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from plugins.local.config import LocalPluginConfig
from plugins.local.manifest import MANIFEST
from plugins.local.services import messaging_provider, storage_provider


class LocalPlugin(MessagingPlugin, StoragePlugin):
    def __init__(self) -> None:
        self._config = LocalPluginConfig()
        self._messaging = messaging_provider()
        self._storage = storage_provider()

    @property
    def manifest(self):
        return MANIFEST

    def get_capabilities(self) -> ProviderCapabilities:
        caps = local_sms()
        storage_caps = local_storage()
        merged = ProviderCapabilities(
            provider_name="local",
            sms=caps.sms,
            email=caps.email,
            storage=storage_caps.storage,
            simulated=caps.simulated,
            country_support=caps.country_support,
        )
        return runtime_caps(merged, self, service="storage")

    def is_configured(self) -> bool:
        return True

    def get_messaging_provider(self) -> BaseProvider:
        return self._messaging

    def get_storage_provider(self) -> BaseProvider:
        return self._storage

    def register_providers(self, registry: ProviderRegistry) -> None:
        registry.register(ProviderService.MESSAGING, self._messaging)
        registry.register(ProviderService.STORAGE, self._storage)

    def health(self) -> dict[str, Any]:
        data = super().health()
        data["storage_path"] = self._config.storage_path
        return data


def create_plugin() -> LocalPlugin:
    return LocalPlugin()
