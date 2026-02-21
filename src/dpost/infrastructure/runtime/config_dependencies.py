"""Legacy-backed config and filesystem dependency bindings for runtime bootstrap."""

from dpost.application.config import ConfigService, DeviceConfig, init_config
from dpost.infrastructure.storage.filesystem_utils import init_dirs

__all__ = ["ConfigService", "DeviceConfig", "init_config", "init_dirs"]
