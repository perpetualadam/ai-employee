"""Plugin system — communications OS core. Business code imports interfaces only."""

from app.plugins.manager import PluginManager, get_plugin_manager

__all__ = ["PluginManager", "get_plugin_manager"]
