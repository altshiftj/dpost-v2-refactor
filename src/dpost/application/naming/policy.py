"""Application facade that applies active config to domain naming policies."""

from __future__ import annotations

from typing import Pattern

from dpost.application.config import current
from dpost.domain.naming.prefix_policy import (
    analyze_user_input as analyze_user_input_policy,
)
from dpost.domain.naming.prefix_policy import (
    explain_filename_violation as explain_filename_violation_policy,
)
from dpost.domain.naming.prefix_policy import (
    is_valid_prefix as is_valid_prefix_policy,
)
from dpost.domain.naming.prefix_policy import (
    sanitize_and_validate as sanitize_and_validate_policy,
)
from dpost.domain.naming.prefix_policy import (
    sanitize_prefix as sanitize_prefix_policy,
)


def _id_separator() -> str:
    return current().id_separator


def _filename_pattern() -> Pattern[str]:
    return current().filename_pattern


def is_valid_prefix(raw_prefix: str) -> bool:
    """Validate filename prefix using active runtime naming policy settings."""
    return is_valid_prefix_policy(
        raw_prefix,
        filename_pattern=_filename_pattern(),
        id_separator=_id_separator(),
    )


def sanitize_prefix(raw_prefix: str) -> str:
    """Sanitize filename prefix using active runtime naming separator."""
    return sanitize_prefix_policy(raw_prefix, id_separator=_id_separator())


def sanitize_and_validate(raw_prefix: str) -> tuple[str, bool]:
    """Return `(sanitized_prefix, is_valid)` under active naming configuration."""
    return sanitize_and_validate_policy(
        raw_prefix,
        filename_pattern=_filename_pattern(),
        id_separator=_id_separator(),
    )


def explain_filename_violation(filename: str) -> dict:
    """Analyze violation details for a filename under active naming settings."""
    return explain_filename_violation_policy(
        filename,
        filename_pattern=_filename_pattern(),
        id_separator=_id_separator(),
    )


def analyze_user_input(dialog_result: dict | None) -> dict:
    """Validate/sanitize rename dialog values under active naming settings."""
    return analyze_user_input_policy(
        dialog_result,
        filename_pattern=_filename_pattern(),
        id_separator=_id_separator(),
    )
