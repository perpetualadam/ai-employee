from app.plugins.categories import PluginCategory
from app.plugins.manifest import PluginManifest

MANIFEST = PluginManifest(
    plugin_name="deepgram",
    plugin_version="1.0.0",
    plugin_author="AI Employee",
    plugin_description="Deepgram speech-to-text and streaming transcription",
    plugin_category=PluginCategory.SPEECH_TO_TEXT,
    supported_services=("speech_to_text",),
    permissions=("ai", "voice"),
    provider_priority=100,
)
