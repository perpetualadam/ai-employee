"""Specification: all marketplace stub plugins load and expose manifests."""

from __future__ import annotations

import importlib
import unittest

STUB_NAMES = (
    "bandwidth",
    "sinch",
    "messagebird",
    "elevenlabs",
    "postmark",
    "google",
    "microsoft",
    "hubspot",
    "salesforce",
)


class StubPluginsLoadSpecification(unittest.TestCase):
    def test_all_stub_plugins_create_instance(self) -> None:
        for name in STUB_NAMES:
            module = importlib.import_module(f"plugins.{name}.plugin")
            plugin = module.create_plugin()
            self.assertEqual(plugin.manifest.plugin_name, name)
            self.assertFalse(plugin.is_configured())


if __name__ == "__main__":
    unittest.main()
