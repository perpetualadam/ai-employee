"""Tests for postmark stub plugin."""

import unittest

from plugins.postmark.manifest import MANIFEST
from plugins.postmark.plugin import create_plugin


class PostmarkPluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "postmark")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "email")


if __name__ == "__main__":
    unittest.main()
