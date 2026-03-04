"""Concrete processor for V2 rhe_kinexus plugin."""

from __future__ import annotations

from dpost_v2.plugins.devices._device_template.processor import TemplateDeviceProcessor


class DeviceProcessor(TemplateDeviceProcessor):
    """Concrete processor bound to rhe_kinexus settings."""
