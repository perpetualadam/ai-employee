"""Tests for microsoft stub plugin."""

import unittest

from plugins.microsoft.manifest import MANIFEST
from plugins.microsoft.plugin import create_plugin


class MicrosoftPluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "microsoft")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "calendar")


if __name__ == "__main__":
    unittest.main()
