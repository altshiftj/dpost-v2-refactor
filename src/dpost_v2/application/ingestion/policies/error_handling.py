from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ErrorClassification:
    """Normalized exception classification used by failure policies."""

    reason_code: str
    severity: str
    retryable: bool
    stage_id: str | None
    diagnostics: Mapping[str, object]


def _snake_case_type_name(name: str) -> str:
    first_pass = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def classify_exception(
    exc: Exception,
    stage_id: str | None,
) -> ErrorClassification:
    """Classify an exception into deterministic reason/severity/retryability fields."""
    reason_code = _snake_case_type_name(exc.__class__.__name__)
    retryable = isinstance(exc, (TimeoutError, ConnectionError))
    if isinstance(exc, RuntimeError) and "retry" in str(exc).lower():
        retryable = True

    return ErrorClassification(
        reason_code=reason_code,
        severity="error",
        retryable=retryable,
        stage_id=stage_id,
        diagnostics={"message": str(exc), "type": exc.__class__.__name__},
    )
