"""Concrete processor for V2 sem_phenomxl2 plugin."""

from __future__ import annotations

from dpost_v2.plugins.devices._device_template.processor import TemplateDeviceProcessor


class DeviceProcessor(TemplateDeviceProcessor):
    """Concrete processor bound to sem_phenomxl2 settings."""
