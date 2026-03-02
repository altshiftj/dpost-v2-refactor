"""Abstract contract for device specific file processors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Pattern

from dpost.application.config import DeviceConfig
from dpost.domain.records.local_record import LocalRecord


@dataclass(frozen=True)
class ProcessingOutput:
    """Standardised return value from device_specific_processing."""

    final_path: str
    datatype: str
    # Optional file or directory paths to force-upload on this processing pass.
    force_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreprocessingResult:
    """Return value for device_specific_preprocessing hooks."""

    effective_path: str
    prefix_override: str | None = None
    extension_override: str | None = None

    @classmethod
    def passthrough(cls, path: str) -> "PreprocessingResult":
        return cls(effective_path=path)

    @classmethod
    def with_prefix(cls, path: str, prefix: str) -> "PreprocessingResult":
        return cls(effective_path=path, prefix_override=prefix)

    @classmethod
    def with_extension(cls, path: str, extension: str) -> "PreprocessingResult":
        return cls(effective_path=path, extension_override=extension)


class ProbeDecision(Enum):
    """Discrete outcomes returned by FileProcessorABS.probe_file."""

    MATCH = auto()
    MISMATCH = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class FileProbeResult:
    """Represents compatibility assessment between a file and a processor."""

    decision: ProbeDecision
    confidence: float = 0.0
    reason: str | None = None

    @classmethod
    def match(
        cls, confidence: float = 1.0, reason: str | None = None
    ) -> "FileProbeResult":
        """Return a result indicating the processor positively identified the file."""

        return cls(ProbeDecision.MATCH, confidence, reason)

    @classmethod
    def mismatch(cls, reason: str | None = None) -> "FileProbeResult":
        """Return a result indicating the processor determined the file does not belong."""

        return cls(ProbeDecision.MISMATCH, 0.0, reason)

    @classmethod
    def unknown(cls, reason: str | None = None) -> "FileProbeResult":
        """Return an inconclusive result, allowing other processors to decide."""

        return cls(ProbeDecision.UNKNOWN, 0.0, reason)

    def is_match(self) -> bool:
        """True when the probe produced a positive match."""

        return self.decision is ProbeDecision.MATCH

    def is_mismatch(self) -> bool:
        """True when the probe explicitly rejected the file."""

        return self.decision is ProbeDecision.MISMATCH

    def is_definitive(self) -> bool:
        """True when the probe has an explicit stance (match or mismatch)."""

        return self.decision is not ProbeDecision.UNKNOWN


class FileProcessorABS(ABC):
    """Processors transform raw artefacts into organised records."""

    def __init__(self, device_config: DeviceConfig):
        self.device_config = device_config

    def device_specific_preprocessing(
        self, src_path: str
    ) -> PreprocessingResult | None:
        """Give processors a hook to stage or normalise incoming files.

        Returning `None` keeps the item in a deferred state (e.g. waiting for
        a paired file). Returning a PreprocessingResult continues the pipeline
        using the declared effective path and optional prefix/extension overrides.
        """

        return PreprocessingResult.passthrough(src_path)

    def matches_file(self, filepath: str) -> bool:
        """Optional hint to quickly filter compatible files."""

        return True

    def is_appendable(
        self, record: LocalRecord, filename_prefix: str, extension: str
    ) -> bool:
        """Whether an item may be appended to an existing record."""

        return True

    def probe_file(self, filepath: str) -> FileProbeResult:
        """Inspect a file to confirm it belongs to this processor.

        The default implementation is intentionally conservative and returns
        FileProbeResult.unknown(), allowing existing processors to rely solely
        on extension or folder routing. Device-specific processors can override
        this method to read headers or metadata and return a more definitive
                outcome.

                Implementors should follow these guidelines:
                - Keep reads lightweight: prefer inspecting only the first 4–8KB.
                - Be robust to encoding issues; ignore undecodable bytes.
                - Return MATCH with a confidence in [0.5, 1.0] when clear evidence is found.
                    Calibrate confidence heuristically and document your rationale.
                - Return MISMATCH when you are confident the file is not yours.
                - Return UNKNOWN for binary formats or when content is inconclusive to
                    allow other processors to decide.
        """

        return FileProbeResult.unknown()

    def should_queue_modified(self, path: str) -> bool:
        """Return True when modified events should be queued for this path."""

        return False

    def configure_runtime_context(
        self,
        *,
        id_separator: str | None = None,
        filename_pattern: Pattern[str] | None = None,
        dest_dir: str | None = None,
        rename_dir: str | None = None,
        exception_dir: str | None = None,
        current_device=None,
    ) -> None:
        """Optionally apply runtime wiring context after processor construction.

        The default implementation is a no-op so existing processors remain
        compatible. Processors may override this to capture runtime naming or
        storage settings that are only known after plugin instantiation.
        """

        return None

    @abstractmethod
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        """Perform the actual move/rename and return final metadata."""
