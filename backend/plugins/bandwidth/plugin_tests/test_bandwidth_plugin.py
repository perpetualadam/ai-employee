"""Tests for bandwidth stub plugin."""

import unittest

from plugins.bandwidth.manifest import MANIFEST
from plugins.bandwidth.plugin import create_plugin


class BandwidthPluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "bandwidth")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "telephony")


if __name__ == "__main__":
    unittest.main()
