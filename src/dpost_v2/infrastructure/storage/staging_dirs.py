"""Deterministic staging directory derivation and policy helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class StagingDirsError(RuntimeError):
    """Base error for staging directory policy failures."""


class StagingDirsConfigError(StagingDirsError):
    """Raised when required staging configuration is missing."""


class StagingDirsSafetyError(StagingDirsError):
    """Raised when a derived path escapes configured root scope."""


class StagingDirsProvisionError(StagingDirsError):
    """Raised when directory provisioning fails."""


class StagingDirsTokenError(StagingDirsError):
    """Raised when profile/mode/device tokens are unsupported."""


@dataclass(frozen=True, slots=True)
class StagingLayout:
    """Canonical staging bucket path set."""

    root: Path
    intake: Path
    staging: Path
    processed: Path
    rejected: Path
    archive: Path


def derive_staging_layout(
    *,
    root: str | Path,
    profile: str,
    mode: str,
    processing_date: date,
    device_token: str,
    create_on_demand: bool = False,
    archive_override: str | Path | None = None,
) -> StagingLayout:
    """Derive deterministic bucket paths from runtime tokens."""
    root_path = Path(root).expanduser().resolve()
    if not str(root_path):
        raise StagingDirsConfigError("root must resolve to a concrete path")

    normalized_profile = _validate_token("profile", profile)
    normalized_mode = _validate_token("mode", mode)
    normalized_device = _validate_token("device_token", device_token)
    date_token = processing_date.isoformat()

    partition = root_path / normalized_profile / normalized_mode / normalized_device
    intake = partition / "intake" / date_token
    staging = partition / "staging" / date_token
    processed = partition / "processed"
    rejected = partition / "rejected"
    archive = (
        Path(archive_override).expanduser()
        if archive_override is not None
        else partition / "archive"
    )
    archive = archive if archive.is_absolute() else root_path / archive
    archive = archive.resolve(strict=False)

    layout = StagingLayout(
        root=root_path,
        intake=_guard_root_scope(root_path, intake),
        staging=_guard_root_scope(root_path, staging),
        processed=_guard_root_scope(root_path, processed),
        rejected=_guard_root_scope(root_path, rejected),
        archive=_guard_root_scope(root_path, archive),
    )

    if create_on_demand:
        try:
            for path in (layout.intake, layout.staging, layout.processed, layout.rejected, layout.archive):
                path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StagingDirsProvisionError(f"failed to provision directories: {exc}") from exc

    return layout


def cleanup_candidates(
    layout: StagingLayout,
    candidate_paths: Iterable[str | Path],
) -> tuple[Path, ...]:
    """Filter retention candidates, excluding active intake/staging buckets."""
    filtered: list[Path] = []
    for raw_path in candidate_paths:
        candidate = Path(raw_path).expanduser().resolve(strict=False)
        if _is_within(candidate, layout.intake) or _is_within(candidate, layout.staging):
            continue
        filtered.append(candidate)
    return tuple(filtered)


def _validate_token(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StagingDirsTokenError(f"{field_name} must be non-empty")
    normalized = value.strip()
    if not _TOKEN_PATTERN.fullmatch(normalized):
        raise StagingDirsTokenError(f"unsupported token value for {field_name}: {value!r}")
    return normalized


def _guard_root_scope(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise StagingDirsSafetyError(f"path escapes configured root: {resolved}") from exc
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

