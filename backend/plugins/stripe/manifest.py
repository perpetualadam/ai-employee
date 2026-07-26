from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="stripe",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="Stripe billing and subscription payments",
    plugin_category=PluginCategory.PAYMENTS,
    supported_services=("payments",),
    permissions=("payments", "database"),
    provider_priority=100,
)
