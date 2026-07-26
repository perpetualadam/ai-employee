from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="messagebird",
    category=PluginCategory.MESSAGING,
    description="MessageBird messaging plugin",
    services=('messaging',),
    permissions=('sms',),
)
