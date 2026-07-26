"""Plugin health aggregation."""

from __future__ import annotations

from typing import Any

from app.plugins.interfaces import BasePlugin


class PluginHealthService:
    def check_all(self, plugins: dict[str, BasePlugin]) -> dict[str, Any]:
        report: dict[str, Any] = {}
        for name, plugin in plugins.items():
            report[name] = plugin.health()
        healthy = sum(1 for entry in report.values() if entry.get("configured"))
        return {
            "plugins": report,
            "total": len(report),
            "configured_count": healthy,
        }

    def check_plugin(self, plugin: BasePlugin) -> dict[str, Any]:
        return plugin.health()
