from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="sinch",
    category=PluginCategory.TELEPHONY,
    description="Sinch telephony and messaging plugin",
    services=('telephony', 'messaging'),
    permissions=('voice', 'sms'),
)
