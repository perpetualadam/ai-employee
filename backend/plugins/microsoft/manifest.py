from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="microsoft",
    category=PluginCategory.CALENDAR,
    description="Microsoft Outlook calendar plugin",
    services=('calendar',),
    permissions=('calendar',),
)
