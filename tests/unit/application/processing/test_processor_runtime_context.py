"""Unit coverage for processor runtime-context helper extraction seam."""

from __future__ import annotations

from dpost.application.processing.processor_runtime_context import (
    ProcessorRuntimeContext,
    apply_processor_runtime_context,
    build_processor_runtime_context,
)
from tests.helpers.fake_processor import DummyProcessor


def test_build_processor_runtime_context_reads_active_config(config_service) -> None:
    """Build runtime context payload from current config naming/path settings."""
    active_config = config_service.current

    context = build_processor_runtime_context(active_config)

    assert context == ProcessorRuntimeContext(
        id_separator=active_config.id_separator,
        filename_pattern=active_config.filename_pattern,
        dest_dir=str(active_config.paths.dest_dir),
        rename_dir=str(active_config.paths.rename_dir),
        exception_dir=str(active_config.paths.exceptions_dir),
    )


def test_apply_processor_runtime_context_forwards_context_and_device(
    config_service,
) -> None:
    """Apply helper should forward explicit runtime context values to processor."""

    class _ProcessorWithContext(DummyProcessor):
        def __init__(self) -> None:
            super().__init__()
            self.context_calls: list[dict[str, object | None]] = []

        def configure_runtime_context(
            self,
            *,
            id_separator: str | None = None,
            filename_pattern=None,
            dest_dir: str | None = None,
            rename_dir: str | None = None,
            exception_dir: str | None = None,
            current_device=None,
        ) -> None:
            self.context_calls.append(
                {
                    "id_separator": id_separator,
                    "filename_pattern": filename_pattern,
                    "dest_dir": dest_dir,
                    "rename_dir": rename_dir,
                    "exception_dir": exception_dir,
                    "current_device": current_device,
                }
            )

    processor = _ProcessorWithContext()
    context = build_processor_runtime_context(config_service.current)
    device = config_service.devices[0]

    apply_processor_runtime_context(processor, device, context)

    assert processor.context_calls == [
        {
            "id_separator": config_service.current.id_separator,
            "filename_pattern": config_service.current.filename_pattern,
            "dest_dir": str(config_service.current.paths.dest_dir),
            "rename_dir": str(config_service.current.paths.rename_dir),
            "exception_dir": str(config_service.current.paths.exceptions_dir),
            "current_device": device,
        }
    ]
