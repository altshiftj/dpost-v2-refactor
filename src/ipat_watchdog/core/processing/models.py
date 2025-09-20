"""Lightweight domain models that unify the processing pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from ipat_watchdog.core.config.device_settings_base import DeviceSettings
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.records.local_record import LocalRecord


class RoutingDecision(Enum):
    """Discrete routing outcomes for an incoming file."""

    UNAPPENDABLE = "unappendable_record"
    APPEND_TO_SYNCED = "append_to_synced"
    ACCEPT = "valid_name"
    REQUIRE_RENAME = "invalid_name"


class ProcessingStatus(Enum):
    """High-level status returned by the pipeline."""

    PROCESSED = "processed"
    REJECTED = "rejected"
    DEFERRED = "deferred"  # Waiting on additional artefacts (e.g. paired files)


@dataclass(frozen=True)
class ProcessingRequest:
    """Minimal information needed to start processing an item."""

    source: Path
    device_settings: DeviceSettings


@dataclass(frozen=True)
class ProcessingCandidate:
    """File after stability checks and optional preprocessing."""

    original_path: Path
    effective_path: Path
    prefix: str
    extension: str
    processor: FileProcessorABS
    device_settings: DeviceSettings
    preprocessed_path: Optional[Path] = None


@dataclass(frozen=True)
class RouteContext:
    """Context passed to routing/record flows."""

    candidate: ProcessingCandidate
    sanitized_prefix: str
    existing_record: Optional[LocalRecord]
    decision: RoutingDecision


@dataclass(frozen=True)
class ProcessingResult:
    """Outcome emitted by FileProcessManager after handling an item."""

    status: ProcessingStatus
    message: str
    final_path: Optional[Path] = None
