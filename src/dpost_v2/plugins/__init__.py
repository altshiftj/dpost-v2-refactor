"""V2 plugin host/discovery package boundary."""

from dpost_v2.plugins.catalog import PluginCatalogSnapshot, build_catalog
from dpost_v2.plugins.discovery import (
    PluginDescriptor,
    PluginDiscoveryDiagnostics,
    PluginDiscoveryIssue,
    PluginDiscoveryResult,
    discover_from_namespaces,
    discover_plugins,
)
from dpost_v2.plugins.host import PluginHost
from dpost_v2.plugins.profile_selection import (
    PluginSelectionResult,
    select_plugins_for_profile,
)

__all__ = [
    "PluginCatalogSnapshot",
    "PluginDescriptor",
    "PluginDiscoveryDiagnostics",
    "PluginDiscoveryIssue",
    "PluginDiscoveryResult",
    "PluginHost",
    "PluginSelectionResult",
    "build_catalog",
    "discover_from_namespaces",
    "discover_plugins",
    "select_plugins_for_profile",
]
