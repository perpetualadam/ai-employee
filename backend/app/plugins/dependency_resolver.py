"""Resolve plugin dependency order for startup."""

from __future__ import annotations

from app.plugins.interfaces import BasePlugin


class PluginDependencyResolver:
    def resolve_install_order(self, plugins: dict[str, BasePlugin]) -> list[str]:
        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise ValueError(f"Circular plugin dependency detected at '{name}'")
            visiting.add(name)
            plugin = plugins.get(name)
            if plugin is None:
                raise KeyError(f"Plugin dependency '{name}' is not installed")
            for dep in plugin.manifest.dependencies:
                if dep in plugins:
                    visit(dep)
            visiting.remove(name)
            visited.add(name)
            ordered.append(name)

        for name in sorted(plugins.keys()):
            visit(name)
        return ordered

    def validate_dependencies(self, plugins: dict[str, BasePlugin]) -> list[str]:
        errors: list[str] = []
        for name, plugin in plugins.items():
            for dep in plugin.manifest.dependencies:
                if dep not in plugins:
                    errors.append(f"Plugin '{name}' requires missing dependency '{dep}'")
        return errors

    def validate_permissions(self, plugins: dict[str, BasePlugin]) -> list[str]:
        errors: list[str] = []
        allowed = {
            "sms",
            "voice",
            "calendar",
            "email",
            "storage",
            "database",
            "ai",
            "payments",
            "webhook",
            "crm",
        }
        for name, plugin in plugins.items():
            for perm in plugin.manifest.permissions:
                if perm.lower() not in allowed:
                    errors.append(f"Plugin '{name}' declares unknown permission '{perm}'")
        return errors
