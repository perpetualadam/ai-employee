"""Plugin manifest — declarative metadata for discovery and marketplace readiness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.plugins.categories import PluginCategory


CORE_VERSION = "0.1.0"


@dataclass(frozen=True)
class PluginManifest:
    plugin_name: str
    plugin_version: str
    plugin_author: str
    plugin_description: str
    plugin_category: PluginCategory
    supported_services: tuple[str, ...] = ()
    supported_countries: frozenset[str] = field(default_factory=frozenset)
    dependencies: tuple[str, ...] = ()
    minimum_core_version: str = CORE_VERSION
    configuration_schema: dict[str, Any] = field(default_factory=dict)
    permissions: tuple[str, ...] = ()
    health_endpoint: str | None = None
    provider_priority: int = 100
    provider_weight: int = 100
    enabled_by_default: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "plugin_version": self.plugin_version,
            "plugin_author": self.plugin_author,
            "plugin_description": self.plugin_description,
            "plugin_category": self.plugin_category.value,
            "supported_services": list(self.supported_services),
            "supported_countries": sorted(self.supported_countries),
            "dependencies": list(self.dependencies),
            "minimum_core_version": self.minimum_core_version,
            "configuration_schema": self.configuration_schema,
            "permissions": list(self.permissions),
            "health_endpoint": self.health_endpoint,
            "provider_priority": self.provider_priority,
            "provider_weight": self.provider_weight,
            "enabled_by_default": self.enabled_by_default,
        }
