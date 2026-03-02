"""Application facade that applies active config to domain naming policies."""

from __future__ import annotations

from typing import Pattern

from dpost.domain.naming import identifiers, prefix_policy


def _require_id_separator(id_separator: str) -> str:
    if not id_separator:
        raise ValueError("id_separator must be provided explicitly")
    return id_separator


def _require_filename_pattern(
    filename_pattern: Pattern[str],
) -> Pattern[str]:
    if filename_pattern is None:
        raise ValueError("filename_pattern must be provided explicitly")
    return filename_pattern


def _require_naming_context(
    *,
    filename_pattern: Pattern[str],
    id_separator: str,
) -> tuple[Pattern[str], str]:
    return (
        _require_filename_pattern(filename_pattern),
        _require_id_separator(id_separator),
    )


def parse_filename(src_path: str) -> tuple[str, str]:
    """Return filename stem and suffix for a path-like string."""
    return identifiers.parse_filename(src_path)


def generate_record_id(
    filename_prefix: str,
    dev_kadi_record_id: str | None = None,
    *,
    id_separator: str,
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
    return identifiers.generate_record_id(
        filename_prefix,
        dev_kadi_record_id=resolved_record_id,
        id_separator=separator,
    )


def generate_file_id(
    filename_prefix: str,
    device_abbr: str | None = None,
    *,
    id_separator: str,
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
    return identifiers.generate_file_id(
        filename_prefix,
        device_abbr=resolved_device_abbr,
        id_separator=separator,
    )


def is_valid_prefix(
    raw_prefix: str,
    *,
    filename_pattern: Pattern[str],
    id_separator: str,
) -> bool:
    """Validate filename prefix using explicit naming policy settings."""
    pattern, separator = _require_naming_context(
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    )
    return prefix_policy.is_valid_prefix(
        raw_prefix,
        filename_pattern=pattern,
        id_separator=separator,
    )


def sanitize_prefix(raw_prefix: str, *, id_separator: str) -> str:
    """Sanitize filename prefix using explicit naming separator."""
    separator = _require_id_separator(id_separator)
    return prefix_policy.sanitize_prefix(
        raw_prefix,
        id_separator=separator,
    )


def sanitize_and_validate(
    raw_prefix: str,
    *,
    filename_pattern: Pattern[str],
    id_separator: str,
) -> tuple[str, bool]:
    """Return `(sanitized_prefix, is_valid)` under explicit naming configuration."""
    pattern, separator = _require_naming_context(
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    )
    return prefix_policy.sanitize_and_validate(
        raw_prefix,
        filename_pattern=pattern,
        id_separator=separator,
    )


def explain_filename_violation(
    filename: str,
    *,
    filename_pattern: Pattern[str],
    id_separator: str,
) -> dict:
    """Analyze violation details for a filename under explicit naming settings."""
    pattern, separator = _require_naming_context(
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    )
    return prefix_policy.explain_filename_violation(
        filename,
        filename_pattern=pattern,
        id_separator=separator,
    )


def analyze_user_input(
    dialog_result: dict | None,
    *,
    filename_pattern: Pattern[str],
    id_separator: str,
) -> dict:
    """Validate/sanitize rename dialog values under explicit naming settings."""
    pattern, separator = _require_naming_context(
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    )
    return prefix_policy.analyze_user_input(
        dialog_result,
        filename_pattern=pattern,
        id_separator=separator,
    )
