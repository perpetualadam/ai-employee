from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="plivo",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="Plivo telephony, numbers, and messaging plugin",
    plugin_category=PluginCategory.TELEPHONY,
    supported_services=("telephony", "numbers", "regulatory", "messaging"),
    supported_countries=frozenset({"*"}),
    permissions=("sms", "voice", "webhook"),
    provider_priority=88,
)
