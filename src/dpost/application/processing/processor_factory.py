"""Factory that instantiates device specific file processors on demand."""

from __future__ import annotations

from typing import Dict

from dpost.application.processing.file_processor_abstract import FileProcessorABS
from dpost.infrastructure.logging import setup_logger
from dpost.plugins.loading import load_device_plugin

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
        plugin_instance = load_device_plugin(device_id)
        processor = plugin_instance.get_file_processor()
        logger.debug(
            "Loaded processor '%s' for device '%s'", type(processor).__name__, device_id
        )
        return processor
