"""Per-plugin isolated configuration — no cross-plugin secret access."""

from __future__ import annotations

import os
from typing import Any

from app.plugins.manifest import PluginManifest


class PluginConfigurationService:
    """Reads configuration scoped to a single plugin via env prefix."""

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest
        self._prefix = manifest.plugin_name.upper().replace("-", "_")

    @property
    def plugin_name(self) -> str:
        return self._manifest.plugin_name

    def get(self, key: str, default: str = "") -> str:
        env_key = f"{self._prefix}_{key.upper()}"
        return os.environ.get(env_key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        raw = self.get(key, str(default).lower())
        return raw.lower() in ("1", "true", "yes", "on")

    def get_int(self, key: str, default: int = 0) -> int:
        raw = self.get(key, str(default))
        try:
            return int(raw)
        except ValueError:
            return default

    def validate_against_schema(self) -> list[str]:
        errors: list[str] = []
        schema = self._manifest.configuration_schema or {}
        required = schema.get("required") or []
        for field_name in required:
            if not self.get(field_name):
                errors.append(f"Missing required configuration: {field_name}")
        return errors

    def snapshot(self) -> dict[str, Any]:
        """Non-secret configuration snapshot for admin (keys only, not values)."""
        schema = self._manifest.configuration_schema or {}
        fields = schema.get("properties") or {}
        return {
            "plugin": self._manifest.plugin_name,
            "env_prefix": self._prefix,
            "configured_keys": [name for name in fields if self.get(name)],
        }
