"""Domain batch value models for staged preprocessing flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

PairT = TypeVar("PairT")


@dataclass(frozen=True)
class PendingPath:
    path: Path
    created: float


@dataclass(frozen=True)
class CsvNgbPair:
    csv_path: Path
    ngb_path: Path
    created: float


@dataclass(frozen=True)
class ExportRawPair:
    export_path: Path
    raw_path: Path
    created: float


@dataclass(frozen=True)
class FlushBatch(Generic[PairT]):
    prefix: str
    pairs: list[PairT]
    raw_probenname: str | None = None
