from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="local",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="Local filesystem storage and dev SMS/email messaging",
    plugin_category=PluginCategory.STORAGE,
    supported_services=("messaging", "storage", "email"),
    permissions=("sms", "email", "storage"),
    enabled_by_default=True,
    provider_priority=10,
)
