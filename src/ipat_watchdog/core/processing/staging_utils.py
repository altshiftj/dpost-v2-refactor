"""Shared staging helpers for preprocessors that batch related files."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable


def create_unique_stage_dir(
    base_dir: Path,
    prefix: str,
    *,
    marker: str = ".__staged__",
    max_index: int = 1000,
) -> Path:
    """Create a unique staging directory named '<prefix><marker><n>'."""
    for idx in range(1, max_index):
        name = f"{prefix}{marker}{idx}"
        candidate = base_dir / name
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    candidate = base_dir / f"{prefix}{marker}"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def reconstruct_pairs_from_stage(
    stage_dir: Path,
    left_filter: Callable[[Path], bool],
    right_filter: Callable[[Path], bool],
    *,
    marker: str = ".__staged__",
    left_label: str = "left",
    right_label: str = "right",
) -> tuple[str, list[tuple[Path, Path]]]:
    """Reconstruct pairs from a staging folder using stem matching + fallback."""
    prefix = stage_dir.name.split(marker)[0]
    left_items = sorted(
        [p for p in stage_dir.iterdir() if left_filter(p)],
        key=lambda p: p.stat().st_mtime,
    )
    right_items = sorted(
        [p for p in stage_dir.iterdir() if right_filter(p)],
        key=lambda p: p.stat().st_mtime,
    )

    if not left_items or not right_items:
        raise RuntimeError(f"Stage directory {stage_dir} missing expected files")

    pairs: list[tuple[Path, Path]] = []
    unmatched_left: list[Path] = []
    used_right: set[Path] = set()
    right_by_stem = {p.stem: p for p in right_items}

    for left in left_items:
        right = right_by_stem.get(left.stem)
        if right is not None and right not in used_right:
            pairs.append((left, right))
            used_right.add(right)
        else:
            unmatched_left.append(left)

    remaining_right = [p for p in right_items if p not in used_right]
    for left, right in zip(unmatched_left, remaining_right):
        pairs.append((left, right))

    if not pairs:
        raise RuntimeError(
            f"No {left_label}/{right_label} pairs found in staging folder {stage_dir}"
        )

    return prefix, pairs


def find_stale_stage_dirs(
    parent: Path,
    *,
    marker: str,
    ttl_seconds: float,
    now: float,
    active: Iterable[str] | None = None,
) -> list[Path]:
    """Return staging directories older than TTL and not currently active."""
    active_set = set(active) if active else set()
    stale: list[Path] = []
    for child in parent.iterdir():
        if not child.is_dir() or marker not in child.name:
            continue
        if str(child) in active_set:
            continue
        try:
            age = now - child.stat().st_mtime
        except Exception:
            age = ttl_seconds + 1
        if age > ttl_seconds:
            stale.append(child)
    return stale
