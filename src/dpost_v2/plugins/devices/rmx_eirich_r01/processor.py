"""Concrete processor for V2 rmx_eirich_r01 plugin."""

from __future__ import annotations

from dpost_v2.plugins.devices._device_template.processor import TemplateDeviceProcessor


class DeviceProcessor(TemplateDeviceProcessor):
    """Concrete processor bound to rmx_eirich_r01 settings."""
