"""Specification: local platform plugin registers messaging and storage."""

from __future__ import annotations

import unittest

from app.plugins.loader import PluginLoader
from app.plugins.manager import bootstrap_plugins
from app.providers.registry import reset_registry
from app.providers.services import ProviderService


class LocalPluginSpecification(unittest.TestCase):
    def setUp(self) -> None:
        self.provider_registry = reset_registry(for_tests=True)

    def test_local_plugin_discovered(self) -> None:
        loader = PluginLoader()
        names = {p.manifest.plugin_name for p in loader.discover()}
        self.assertIn("local", names)

    def test_local_plugin_registers_messaging_and_storage(self) -> None:
        bootstrap_plugins(provider_registry=self.provider_registry, reset=True)
        messaging = self.provider_registry.list_registered(ProviderService.MESSAGING)
        storage = self.provider_registry.list_registered(ProviderService.STORAGE)
        self.assertIn("local_sms", messaging)
        self.assertIn("local", storage)

    def test_core_manager_no_longer_imports_local_sms_directly(self) -> None:
        import app.plugins.manager as manager_module

        source = open(manager_module.__file__, encoding="utf-8").read()
        self.assertNotIn("LocalSMSProvider", source)


if __name__ == "__main__":
    unittest.main()
