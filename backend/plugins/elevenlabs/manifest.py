from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="elevenlabs",
    category=PluginCategory.TEXT_TO_SPEECH,
    description="ElevenLabs text-to-speech plugin",
    services=('text_to_speech',),
    permissions=('ai',),
)
