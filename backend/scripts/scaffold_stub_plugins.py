"""Scaffold full file structure for marketplace stub plugins."""

from __future__ import annotations

from pathlib import Path

STUBS = [
    ("bandwidth", "TELEPHONY", "Bandwidth telephony plugin", ("telephony", "numbers"), ("voice", "sms")),
    ("sinch", "TELEPHONY", "Sinch telephony and messaging plugin", ("telephony", "messaging"), ("voice", "sms")),
    ("messagebird", "MESSAGING", "MessageBird messaging plugin", ("messaging",), ("sms",)),
    ("elevenlabs", "TEXT_TO_SPEECH", "ElevenLabs text-to-speech plugin", ("text_to_speech",), ("ai",)),
    ("postmark", "EMAIL", "Postmark email delivery plugin", ("email",), ("email",)),
    ("google", "CALENDAR", "Google Calendar plugin", ("calendar",), ("calendar",)),
    ("microsoft", "CALENDAR", "Microsoft Outlook calendar plugin", ("calendar",), ("calendar",)),
    ("hubspot", "CRM", "HubSpot CRM sync plugin", ("crm",), ("crm", "database")),
    ("salesforce", "CRM", "Salesforce CRM sync plugin", ("crm",), ("crm", "database")),
]

ROOT = Path(__file__).resolve().parents[1] / "plugins"


def _manifest_py(name: str, category: str, desc: str, services: tuple[str, ...], perms: tuple[str, ...]) -> str:
    return f'''from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="{name}",
    category=PluginCategory.{category},
    description="{desc}",
    services={services!r},
    permissions={perms!r},
)
'''


def _config_py(name: str) -> str:
    return f'''from plugins._shared.stub_components import StubPluginConfig

config = StubPluginConfig("{name}")
'''


def _services_py(name: str) -> str:
    return f'''"""{name.title()} plugin services — marketplace stub."""


class {name.title()}PluginServices:
    """Placeholder for future {name.title()} API integration."""

    def __init__(self) -> None:
        self.ready = False
'''


def _models_py(name: str) -> str:
    return f'''from plugins._shared.stub_components import StubPluginMetadata

DEFAULT_METADATA = StubPluginMetadata(plugin_name="{name}")
'''


def _dependencies_py() -> str:
    return '''from plugins._shared.stub_components import StubPluginDependencies

DEPENDENCIES = StubPluginDependencies.REQUIRES
'''


def _health_py() -> str:
    return '''from plugins._shared.stub_components import StubPluginHealth

check_health = StubPluginHealth.check
'''


def _plugin_py(name: str) -> str:
    return f'''from plugins._shared.stub_components import build_stub_plugin_class
from plugins.{name}.manifest import MANIFEST

Plugin = build_stub_plugin_class(MANIFEST)


def create_plugin():
    return Plugin()
'''


def _readme(name: str, desc: str) -> str:
    return f"""# {name.title()} Plugin

{desc}

Marketplace-ready stub — enable and configure via plugin settings when the integration is implemented.
"""


def _test_py(name: str, category: str) -> str:
    return f'''"""Tests for {name} stub plugin."""

import unittest

from plugins.{name}.manifest import MANIFEST
from plugins.{name}.plugin import create_plugin


class {name.title()}PluginSpecification(unittest.TestCase):
    def test_manifest_name(self) -> None:
        self.assertEqual(MANIFEST.plugin_name, "{name}")

    def test_plugin_is_marketplace_stub(self) -> None:
        plugin = create_plugin()
        self.assertFalse(plugin.is_configured())
        self.assertEqual(MANIFEST.plugin_category.value, "{category.lower()}")


if __name__ == "__main__":
    unittest.main()
'''


def scaffold() -> None:
    for name, category, desc, services, perms in STUBS:
        plugin_dir = ROOT / name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "manifest.py").write_text(_manifest_py(name, category, desc, services, perms), encoding="utf-8")
        (plugin_dir / "config.py").write_text(_config_py(name), encoding="utf-8")
        (plugin_dir / "services.py").write_text(_services_py(name), encoding="utf-8")
        (plugin_dir / "models.py").write_text(_models_py(name), encoding="utf-8")
        (plugin_dir / "dependencies.py").write_text(_dependencies_py(), encoding="utf-8")
        (plugin_dir / "health.py").write_text(_health_py(), encoding="utf-8")
        (plugin_dir / "plugin.py").write_text(_plugin_py(name), encoding="utf-8")
        (plugin_dir / "README.md").write_text(_readme(name, desc), encoding="utf-8")
        tests_dir = plugin_dir / "plugin_tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        (tests_dir / f"test_{name}_plugin.py").write_text(_test_py(name, category), encoding="utf-8")
        print(f"scaffolded {name}")


if __name__ == "__main__":
    scaffold()
