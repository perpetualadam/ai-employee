"""Specification: marketplace stub plugins expose full package structure."""

from __future__ import annotations

import unittest
from pathlib import Path

PLUGINS_ROOT = Path(__file__).resolve().parents[1] / "plugins"
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
REQUIRED_FILES = (
    "manifest.py",
    "plugin.py",
    "config.py",
    "services.py",
    "models.py",
    "dependencies.py",
    "health.py",
    "README.md",
)


class StubPluginStructureSpecification(unittest.TestCase):
    def test_stub_plugins_have_required_files(self) -> None:
        for name in STUB_NAMES:
            plugin_dir = PLUGINS_ROOT / name
            for filename in REQUIRED_FILES:
                path = plugin_dir / filename
                self.assertTrue(path.is_file(), f"{name} missing {filename}")
        test_file = plugin_dir / "plugin_tests" / f"test_{name}_plugin.py"
        self.assertTrue(test_file.is_file(), f"{name} missing plugin_tests")

    def test_hubspot_stub_loads_via_loader(self) -> None:
        from app.plugins.loader import PluginLoader

        loader = PluginLoader()
        plugins = {p.manifest.plugin_name: p for p in loader.discover()}
        self.assertIn("hubspot", plugins)
        self.assertFalse(plugins["hubspot"].is_configured())


if __name__ == "__main__":
    unittest.main()
