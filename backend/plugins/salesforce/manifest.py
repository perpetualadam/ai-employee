from app.plugins.categories import PluginCategory
from plugins._shared.stub_components import build_stub_manifest

MANIFEST = build_stub_manifest(
    name="salesforce",
    category=PluginCategory.CRM,
    description="Salesforce CRM sync plugin",
    services=('crm',),
    permissions=('crm', 'database'),
)
