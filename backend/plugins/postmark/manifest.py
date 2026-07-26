from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="postmark",
    category=PluginCategory.EMAIL,
    description="Postmark email delivery plugin",
    services=('email',),
    permissions=('email',),
)
