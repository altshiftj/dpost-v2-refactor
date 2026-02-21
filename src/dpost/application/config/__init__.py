"""dpost config boundary exports for runtime and application modules."""

from ipat_watchdog.core.config import (
    ConfigService,
    DeviceConfig,
    StabilityOverride,
    current,
    get_service,
    init_config,
)

__all__ = [
    "ConfigService",
    "DeviceConfig",
    "StabilityOverride",
    "current",
    "get_service",
    "init_config",
]
