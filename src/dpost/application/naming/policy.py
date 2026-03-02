"""Application facade that applies active config to domain naming policies."""

from __future__ import annotations

from typing import Pattern

from dpost.domain.naming.identifiers import generate_file_id as generate_file_id_policy
from dpost.domain.naming.identifiers import (
    generate_record_id as generate_record_id_policy,
)
from dpost.domain.naming.identifiers import parse_filename as parse_filename_policy
from dpost.domain.naming.prefix_policy import (
    analyze_user_input as analyze_user_input_policy,
)
from dpost.domain.naming.prefix_policy import (
    explain_filename_violation as explain_filename_violation_policy,
)
from dpost.domain.naming.prefix_policy import is_valid_prefix as is_valid_prefix_policy
from dpost.domain.naming.prefix_policy import (
    sanitize_and_validate as sanitize_and_validate_policy,
)
from dpost.domain.naming.prefix_policy import sanitize_prefix as sanitize_prefix_policy


def _require_id_separator(id_separator: str | None) -> str:
    if not id_separator:
        raise ValueError("id_separator must be provided explicitly")
    return id_separator


def _require_filename_pattern(
    filename_pattern: Pattern[str] | None,
) -> Pattern[str]:
    if filename_pattern is None:
        raise ValueError("filename_pattern must be provided explicitly")
    return filename_pattern


def parse_filename(src_path: str) -> tuple[str, str]:
    """Return filename stem and suffix for a path-like string."""
    return parse_filename_policy(src_path)


def generate_record_id(
    filename_prefix: str,
    dev_kadi_record_id: str | None = None,
    *,
    id_separator: str | None = None,
    current_device=None,
) -> str:
    """Generate record identifier from explicit naming and device context."""
    resolved_record_id = dev_kadi_record_id
    if resolved_record_id is None:
        device = current_device
        if device is None or not device.metadata.record_kadi_id:
            raise ValueError(
                "Device context is not set; provide dev_kadi_record_id explicitly or pass current_device."
            )
        resolved_record_id = device.metadata.record_kadi_id
    separator = _require_id_separator(id_separator)
    return generate_record_id_policy(
        filename_prefix,
        dev_kadi_record_id=resolved_record_id,
        id_separator=separator,
    )


def generate_file_id(
    filename_prefix: str,
    device_abbr: str | None = None,
    *,
    id_separator: str | None = None,
    current_device=None,
) -> str:
    """Generate file identifier from explicit naming and device context."""
    resolved_device_abbr = device_abbr
    if resolved_device_abbr is None:
        device = current_device
        if device is None or not device.metadata.device_abbr:
            raise ValueError(
                "Device context is not set; provide device_abbr explicitly or pass current_device."
            )
        resolved_device_abbr = device.metadata.device_abbr
    separator = _require_id_separator(id_separator)
    return generate_file_id_policy(
        filename_prefix,
        device_abbr=resolved_device_abbr,
        id_separator=separator,
    )


def is_valid_prefix(
    raw_prefix: str,
    *,
    filename_pattern: Pattern[str] | None = None,
    id_separator: str | None = None,
) -> bool:
    """Validate filename prefix using explicit naming policy settings."""
    pattern = _require_filename_pattern(filename_pattern)
    separator = _require_id_separator(id_separator)
    return is_valid_prefix_policy(
        raw_prefix,
        filename_pattern=pattern,
        id_separator=separator,
    )


def sanitize_prefix(raw_prefix: str, *, id_separator: str | None = None) -> str:
    """Sanitize filename prefix using explicit naming separator."""
    separator = _require_id_separator(id_separator)
    return sanitize_prefix_policy(
        raw_prefix,
        id_separator=separator,
    )


def sanitize_and_validate(
    raw_prefix: str,
    *,
    filename_pattern: Pattern[str] | None = None,
    id_separator: str | None = None,
) -> tuple[str, bool]:
    """Return `(sanitized_prefix, is_valid)` under explicit naming configuration."""
    pattern = _require_filename_pattern(filename_pattern)
    separator = _require_id_separator(id_separator)
    return sanitize_and_validate_policy(
        raw_prefix,
        filename_pattern=pattern,
        id_separator=separator,
    )


def explain_filename_violation(
    filename: str,
    *,
    filename_pattern: Pattern[str] | None = None,
    id_separator: str | None = None,
) -> dict:
    """Analyze violation details for a filename under explicit naming settings."""
    pattern = _require_filename_pattern(filename_pattern)
    separator = _require_id_separator(id_separator)
    return explain_filename_violation_policy(
        filename,
        filename_pattern=pattern,
        id_separator=separator,
    )


def analyze_user_input(
    dialog_result: dict | None,
    *,
    filename_pattern: Pattern[str] | None = None,
    id_separator: str | None = None,
) -> dict:
    """Validate/sanitize rename dialog values under explicit naming settings."""
    pattern = _require_filename_pattern(filename_pattern)
    separator = _require_id_separator(id_separator)
    return analyze_user_input_policy(
        dialog_result,
        filename_pattern=pattern,
        id_separator=separator,
    )
