from plugins._shared.stub_components import build_stub_plugin_class
from plugins.microsoft.manifest import MANIFEST

Plugin = build_stub_plugin_class(MANIFEST)


def create_plugin():
    return Plugin()
