from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="resend",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="Resend transactional email plugin",
    plugin_category=PluginCategory.EMAIL,
    supported_services=("messaging", "email"),
    permissions=("email",),
    provider_priority=100,
)
