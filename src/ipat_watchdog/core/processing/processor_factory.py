"""Factory that instantiates device specific file processors on demand."""
from __future__ import annotations

import importlib
import inspect
from typing import Dict, Type

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.device_plugins.device_plugin import DevicePlugin

logger = setup_logger(__name__)


class FileProcessorFactory:
    """Load and cache processor instances keyed by device identifier."""

    def __init__(self) -> None:
        self._cache: Dict[str, FileProcessorABS] = {}

    def get_for_device(self, device_id: str) -> FileProcessorABS:
        if device_id not in self._cache:
            self._cache[device_id] = self._load(device_id)
        return self._cache[device_id]

    def _load(self, device_id: str) -> FileProcessorABS:
        try:
            module = importlib.import_module(f"ipat_watchdog.device_plugins.{device_id}.plugin")
        except ImportError as exc:  # pragma: no cover - defensive logging
            logger.error("Unable to import plugin module for device '%s': %s", device_id, exc)
            raise

        plugin_class = self._discover_plugin_class(module, device_id)
        plugin_instance: DevicePlugin = plugin_class()
        processor = plugin_instance.get_file_processor()
        logger.debug("Loaded processor '%s' for device '%s'", type(processor).__name__, device_id)
        return processor

    @staticmethod
    def _discover_plugin_class(module, device_id: str) -> Type[DevicePlugin]:
        for attr in module.__dict__.values():
            if inspect.isclass(attr) and issubclass(attr, DevicePlugin) and not inspect.isabstract(attr):
                return attr
        raise ImportError(f"No concrete DevicePlugin found for device '{device_id}'")
