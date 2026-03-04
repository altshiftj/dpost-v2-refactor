"""Helpers for deriving normalized processing candidate metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dpost.application.naming.policy import parse_filename
from dpost.application.processing.file_processor_abstract import PreprocessingResult


@dataclass(frozen=True)
class CandidateMetadata:
    """Normalized metadata required to construct a processing candidate."""

    prefix: str
    extension: str
    effective_path: Path
    preprocessed_path: Path | None


def derive_candidate_metadata(
    source_path: Path,
    preprocessed: PreprocessingResult,
    *,
    strip_internal_stage_suffix: Callable[[Path], Path],
    parse_filename_fn: Callable[[str], tuple[str, str]] = parse_filename,
) -> CandidateMetadata:
    """Resolve prefix/extension and effective paths for candidate routing."""
    effective_path = Path(preprocessed.effective_path)

    parse_target = strip_internal_stage_suffix(effective_path)
    prefix, extension = parse_filename_fn(str(parse_target))
    if preprocessed.prefix_override:
        prefix = preprocessed.prefix_override
    if preprocessed.extension_override:
        extension = preprocessed.extension_override

    if not effective_path.exists():
        effective_path = source_path
        parse_target = strip_internal_stage_suffix(effective_path)
        prefix, extension = parse_filename_fn(str(parse_target))

    preprocessed_path = None
    explicit_path = Path(preprocessed.effective_path)
    if explicit_path != effective_path and explicit_path.exists():
        preprocessed_path = explicit_path

    return CandidateMetadata(
        prefix=prefix,
        extension=extension,
        effective_path=effective_path,
        preprocessed_path=preprocessed_path,
    )
