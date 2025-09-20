"""Abstract contract for device specific file processors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from ipat_watchdog.core.records.local_record import LocalRecord


@dataclass(frozen=True)
class ProcessingOutput:
    """Standardised return value from device_specific_processing."""

    final_path: str
    datatype: str


class FileProcessorABS(ABC):
    """Processors transform raw artefacts into organised records."""

    def device_specific_preprocessing(self, src_path: str) -> str | None:
        """Give processors a hook to stage or normalise incoming files.

        Returning `None` keeps the item in a deferred state (e.g. waiting for
        a paired file). Returning a string continues the pipeline using that
        path as the effective artefact.
        """
        return src_path

    def matches_file(self, filepath: str) -> bool:
        """Optional hint to quickly filter compatible files."""
        return True

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        """Whether an item may be appended to an existing record."""
        return True

    @abstractmethod
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        """Perform the actual move/rename and return final metadata."""


class FileProcessorBase(FileProcessorABS):
    """Convenience subclass providing permissive defaults."""

    pass
