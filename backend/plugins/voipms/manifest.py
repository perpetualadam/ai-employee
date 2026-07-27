from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="voipms",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="VoIP.ms SMS, DID provisioning, and SIP routing plugin",
    plugin_category=PluginCategory.TELEPHONY,
    supported_services=("telephony", "numbers", "regulatory", "messaging"),
    supported_countries=frozenset({"US", "CA"}),
    permissions=("sms", "voice", "webhook"),
    provider_priority=80,
)
