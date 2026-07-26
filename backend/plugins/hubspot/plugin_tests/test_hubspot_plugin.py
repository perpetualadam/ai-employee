"""Tests for hubspot stub plugin."""

import unittest

from plugins.hubspot.manifest import MANIFEST
from plugins.hubspot.plugin import create_plugin


class HubspotPluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "hubspot")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "crm")


if __name__ == "__main__":
    unittest.main()
