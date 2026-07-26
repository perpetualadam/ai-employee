"""Tests for messagebird stub plugin."""

import unittest

from plugins.messagebird.manifest import MANIFEST
from plugins.messagebird.plugin import create_plugin


class MessagebirdPluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "messagebird")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "messaging")


if __name__ == "__main__":
    unittest.main()
