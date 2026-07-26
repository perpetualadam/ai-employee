from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="google",
    category=PluginCategory.CALENDAR,
    description="Google Calendar plugin",
    services=('calendar',),
    permissions=('calendar',),
)
