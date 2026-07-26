"""Tests for salesforce stub plugin."""

import unittest

from plugins.salesforce.manifest import MANIFEST
from plugins.salesforce.plugin import create_plugin


class SalesforcePluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "salesforce")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "crm")


if __name__ == "__main__":
    unittest.main()
