"""Tests for elevenlabs stub plugin."""

import unittest

from plugins.elevenlabs.manifest import MANIFEST
from plugins.elevenlabs.plugin import create_plugin


class ElevenlabsPluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "elevenlabs")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "text_to_speech")


if __name__ == "__main__":
    unittest.main()
