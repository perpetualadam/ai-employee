"""Tests for google stub plugin."""

import unittest

from plugins.google.manifest import MANIFEST
from plugins.google.plugin import create_plugin


class GooglePluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "google")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "calendar")


if __name__ == "__main__":
    unittest.main()
