"""Domain value models for processing workflow decisions and outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from dpost.domain.records.local_record import LocalRecord


class DeviceRef(Protocol):
    """Minimal device reference carried by domain processing request/candidate."""


class AppendabilityPolicy(Protocol):
    """Protocol for appendability checks used by domain routing policy."""

    def is_appendable(
        self,
        record: "LocalRecord",
        filename_prefix: str,
        extension: str,
    ) -> bool: ...


class RoutingDecision(Enum):
    """Discrete routing outcomes for an incoming file."""

    UNAPPENDABLE = "unappendable_record"
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
    device: DeviceRef


@dataclass(frozen=True)
class ProcessingCandidate:
    """File after stability checks and optional preprocessing."""

    original_path: Path
    effective_path: Path
    prefix: str
    extension: str
    processor: AppendabilityPolicy
    device: DeviceRef
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
    retry_delay: Optional[float] = None
