"""Unit coverage for device processor factory caching/loading behavior."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

import dpost.application.processing.processor_factory as factory_module


@dataclass
class _PluginStub:
    """Device plugin stub exposing a pre-built file processor."""

    processor: object

    def get_file_processor(self) -> object:
        """Return the configured processor instance."""
        return self.processor


def test_factory_caches_loaded_processor_by_device_id() -> None:
    """Load processor once per device ID and return cached instances afterward."""
    calls: list[str] = []
    processor = object()
    original_loader = factory_module.load_device_plugin
    factory_module.load_device_plugin = lambda device_id: calls.append(device_id) or _PluginStub(processor)
    try:
        factory = factory_module.FileProcessorFactory()
        first = factory.get_for_device("dev-a")
        second = factory.get_for_device("dev-a")
    finally:
        factory_module.load_device_plugin = original_loader

    assert first is processor
    assert second is processor
    assert calls == ["dev-a"]


def test_factory_loads_distinct_processors_for_distinct_devices() -> None:
    """Maintain separate cache entries for different device identifiers."""
    original_loader = factory_module.load_device_plugin
    factory_module.load_device_plugin = (
        lambda device_id: _PluginStub({"device": device_id})
    )
    try:
        factory = factory_module.FileProcessorFactory()
        processor_a = factory.get_for_device("dev-a")
        processor_b = factory.get_for_device("dev-b")
    finally:
        factory_module.load_device_plugin = original_loader

    assert processor_a != processor_b
    assert processor_a["device"] == "dev-a"
    assert processor_b["device"] == "dev-b"


def test_factory_load_logs_processor_type_and_device_id() -> None:
    """Emit debug log with processor type name and source device identifier."""

    class _ProcessorStub:
        """Distinct processor class used to verify debug type-name logging."""

    logger = Mock()
    original_loader = factory_module.load_device_plugin
    original_logger = factory_module.logger
    factory_module.load_device_plugin = lambda _device_id: _PluginStub(_ProcessorStub())
    factory_module.logger = logger
    try:
        factory = factory_module.FileProcessorFactory()
        processor = factory._load("dev-z")
    finally:
        factory_module.load_device_plugin = original_loader
        factory_module.logger = original_logger

    assert isinstance(processor, _ProcessorStub)
    logger.debug.assert_called_once_with(
        "Loaded processor '%s' for device '%s'",
        "_ProcessorStub",
        "dev-z",
    )
