from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="telnyx",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="Telnyx telephony, numbers, regulatory, and messaging adapter plugin",
    plugin_category=PluginCategory.TELEPHONY,
    supported_services=("telephony", "numbers", "regulatory", "messaging"),
    supported_countries=frozenset({"US", "CA", "GB", "AU", "NZ", "EU", "*"}),
    permissions=("sms", "voice", "webhook", "storage"),
    provider_priority=100,
    provider_weight=100,
    configuration_schema={
        "required": [],
        "properties": {
            "api_key": {"type": "string"},
            "messaging_profile_id": {"type": "string"},
            "texml_connection_id": {"type": "string"},
        },
    },
)
