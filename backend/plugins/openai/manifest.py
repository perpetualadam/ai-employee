from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="openai",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="OpenAI voice AI — STT/TTS and realtime models",
    plugin_category=PluginCategory.VOICE_AI,
    supported_services=("voice",),
    permissions=("ai",),
    provider_priority=100,
)
