from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="bandwidth",
    category=PluginCategory.TELEPHONY,
    description="Bandwidth telephony plugin",
    services=('telephony', 'numbers'),
    permissions=('voice', 'sms'),
)
