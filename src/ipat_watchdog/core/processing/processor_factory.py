"""
File processor factory and cache.

Encapsulates dynamic discovery and instantiation of device-specific
file processors to keep the orchestrator slim.
"""
from __future__ import annotations

from typing import Dict

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS

logger = setup_logger(__name__)


class FileProcessorFactory:
    """Loads and caches file processors for device IDs using plugin modules."""

    def __init__(self) -> None:
        self._cache: Dict[str, FileProcessorABS] = {}

    def get_for_device(self, device_id: str) -> FileProcessorABS:
        if device_id in self._cache:
            return self._cache[device_id]

        try:
            plugin_module = __import__(
                f"ipat_watchdog.device_plugins.{device_id}.plugin", fromlist=[""]
            )

            plugin_class = None
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "get_file_processor")
                    and attr_name.endswith("Plugin")
                    and not getattr(attr, "__abstractmethods__", None)
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise ImportError(f"No plugin class found in {device_id}.plugin")

            plugin_instance = plugin_class()
            processor: FileProcessorABS = plugin_instance.get_file_processor()
            self._cache[device_id] = processor
            return processor

        except ImportError as e:
            logger.error(f"Failed to load processor for device {device_id}: {e}")
            raise
