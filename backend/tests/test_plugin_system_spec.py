"""Specification: plugin-first architecture."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.plugins.events import Events, PluginEvent, get_event_bus
from app.plugins.loader import PluginLoader
from app.plugins.interfaces import TelephonyPlugin
from app.plugins.manager import PluginManager, bootstrap_plugins
from app.plugins.registry import reset_plugin_registry
from app.providers.registry import ProviderRegistry, reset_registry


class PluginLoaderSpecification(unittest.TestCase):
    def test_discovers_installed_plugins(self) -> None:
        loader = PluginLoader()
        plugins = loader.discover()
        names = {p.manifest.plugin_name for p in plugins}
        self.assertIn("telnyx", names)
        self.assertIn("twilio", names)
        self.assertIn("openai", names)
        self.assertIn("stripe", names)
        self.assertIn("hubspot", names)

    def test_manifest_validation(self) -> None:
        loader = PluginLoader()
        plugin = loader.discover()[0]
        self.assertEqual([], PluginLoader.validate_manifest(plugin.manifest))


class PluginManagerSpecification(unittest.TestCase):
    def setUp(self) -> None:
        self.provider_registry = reset_registry(for_tests=True)

    def test_startup_bridges_telephony_providers(self) -> None:
        from app.providers.services import ProviderService

        manager = bootstrap_plugins(provider_registry=self.provider_registry, reset=True)
        registered = self.provider_registry.list_registered(ProviderService.TELEPHONY)
        self.assertIn("mock", registered)
        self.assertIn("telnyx", registered)
        self.assertIn("twilio", registered)
        self.assertGreater(len(manager.registry.list_all()), 5)

    def test_health_check_returns_plugin_status(self) -> None:
        manager = bootstrap_plugins(provider_registry=self.provider_registry, reset=True)
        health = manager.health_check()
        self.assertIn("plugins", health)
        self.assertGreater(health["total"], 0)

    def test_get_telephony_plugin_by_capability_not_name(self) -> None:
        manager = bootstrap_plugins(provider_registry=self.provider_registry, reset=True)
        telephony_plugins = [
            manager.registry.get(name)
            for name in manager.registry.list_enabled()
            if isinstance(manager.registry.get(name), TelephonyPlugin)
        ]
        self.assertGreater(len(telephony_plugins), 0)
        self.assertTrue(telephony_plugins[0].get_capabilities().supports("voice"))


class PluginEventBusSpecification(unittest.TestCase):
    def test_publish_subscribe(self) -> None:
        bus = get_event_bus()
        received: list[str] = []

        def handler(event: PluginEvent) -> None:
            received.append(event.name)

        bus.subscribe(Events.BOOKING_CREATED, handler, subscriber_id="test")
        bus.publish(PluginEvent(name=Events.BOOKING_CREATED, payload={"id": "1"}))
        self.assertEqual(received, [Events.BOOKING_CREATED])


class PluginBootstrapSpecification(unittest.TestCase):
    def test_core_bootstrap_has_no_direct_vendor_imports(self) -> None:
        import app.providers.bootstrap as bootstrap_module

        source = open(bootstrap_module.__file__, encoding="utf-8").read()
        for vendor in ("Telnyx", "Twilio", "Vonage", "OpenAI", "Resend", "stripe"):
            self.assertNotIn(f"import {vendor}", source)
            self.assertNotIn(f"from app.providers.{vendor.lower()}", source)


if __name__ == "__main__":
    unittest.main()
