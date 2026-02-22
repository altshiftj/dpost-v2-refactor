"""Helpers for resolving and expanding force-upload paths after processing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class ResolvedForcePath:
    """Represents one force-path input after record-relative resolution."""

    raw_path: str
    resolved_path: Path
    exists: bool


def resolve_force_paths(
    force_paths: Iterable[str],
    record_path: str,
) -> tuple[ResolvedForcePath, ...]:
    """Resolve force-path entries relative to a record directory."""
    record_root = Path(record_path)
    resolved: list[ResolvedForcePath] = []
    for raw_path in force_paths:
        if not raw_path:
            continue
        path_obj = Path(raw_path)
        if not path_obj.is_absolute():
            path_obj = record_root / path_obj
        resolved.append(
            ResolvedForcePath(
                raw_path=raw_path,
                resolved_path=path_obj,
                exists=path_obj.exists(),
            )
        )
    return tuple(resolved)


def iter_force_unsynced_targets(path: Path) -> Iterator[Path]:
    """Yield files that should be marked unsynced for a force-upload path."""
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_file():
                yield child
        return
    yield path
