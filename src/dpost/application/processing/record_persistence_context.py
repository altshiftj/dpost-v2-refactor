"""Helpers for assembling record persistence context with explicit runtime inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dpost.application.config import DeviceConfig
from dpost.application.processing.file_processor_abstract import FileProcessorABS
from dpost.domain.records.local_record import LocalRecord


@dataclass(frozen=True)
class RecordPersistenceContext:
    """Resolved context used by record persistence stages."""

    record: LocalRecord
    processor: FileProcessorABS
    record_path: str
    file_id: str


def build_record_persistence_context(
    *,
    records,
    existing_record: LocalRecord | None,
    filename_prefix: str,
    device: DeviceConfig | None,
    processor: FileProcessorABS,
    id_separator: str,
    dest_dir: str | Path,
    current_device_provider: Callable[[], DeviceConfig | None],
    get_or_create_record_fn: Callable[
        [object, LocalRecord | None, str, DeviceConfig | None],
        LocalRecord,
    ],
    apply_device_defaults_fn: Callable[[LocalRecord, DeviceConfig | None], None],
    get_record_path_fn: Callable[..., str],
    generate_file_id_fn: Callable[..., str],
) -> RecordPersistenceContext:
    """Resolve record/device/path identifiers for artifact persistence."""
    if not id_separator:
        raise ValueError("id_separator must be provided explicitly")

    resolved_device = device or current_device_provider()
    resolved_record = get_or_create_record_fn(
        records,
        existing_record,
        filename_prefix,
        resolved_device,
    )
    device_abbr = resolved_device.metadata.device_abbr if resolved_device else None
    apply_device_defaults_fn(resolved_record, resolved_device)
    record_path = get_record_path_fn(
        filename_prefix,
        device_abbr,
        id_separator=id_separator,
        dest_dir=dest_dir,
        current_device=resolved_device,
    )
    file_id = generate_file_id_fn(
        filename_prefix,
        device_abbr,
        id_separator=id_separator,
        current_device=resolved_device,
    )
    return RecordPersistenceContext(
        record=resolved_record,
        processor=processor,
        record_path=record_path,
        file_id=file_id,
    )
