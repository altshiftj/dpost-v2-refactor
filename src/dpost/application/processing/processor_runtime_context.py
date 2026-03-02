"""Helpers for applying explicit runtime naming/path context to processors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Pattern

from dpost.application.config import ActiveConfig, DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProcessorABS


@dataclass(frozen=True, slots=True)
class ProcessorRuntimeContext:
    """Explicit runtime context forwarded to processor runtime configuration."""

    id_separator: str
    filename_pattern: Pattern[str]
    dest_dir: str
    rename_dir: str
    exception_dir: str


def build_processor_runtime_context(
    active_config: ActiveConfig,
) -> ProcessorRuntimeContext:
    """Build processor runtime context from resolved active runtime config."""
    return ProcessorRuntimeContext(
        id_separator=active_config.id_separator,
        filename_pattern=active_config.filename_pattern,
        dest_dir=str(active_config.paths.dest_dir),
        rename_dir=str(active_config.paths.rename_dir),
        exception_dir=str(active_config.paths.exceptions_dir),
    )


def apply_processor_runtime_context(
    processor: FileProcessorABS,
    device: DeviceConfig,
    context: ProcessorRuntimeContext,
) -> None:
    """Apply explicit runtime context to a processor instance."""
    processor.configure_runtime_context(
        id_separator=context.id_separator,
        filename_pattern=context.filename_pattern,
        dest_dir=context.dest_dir,
        rename_dir=context.rename_dir,
        exception_dir=context.exception_dir,
        current_device=device,
    )
