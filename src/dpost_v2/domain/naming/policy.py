"""Canonical naming composition policy for V2 domain."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping, Sequence


class NamingPolicyError(ValueError):
    """Base class for naming policy validation errors."""


class NamingMissingSegmentError(NamingPolicyError):
    """Raised when required template segment value is missing."""


class NamingSegmentValidationError(NamingPolicyError):
    """Raised when a segment value violates configured constraints."""


class NamingTemplateError(NamingPolicyError):
    """Raised when template structure or placeholders are invalid."""


class NamingLengthError(NamingPolicyError):
    """Raised when composed name exceeds configured maximum length."""


KNOWN_SEGMENTS = frozenset(
    {
        "prefix",
        "identifier",
        "timestamp",
        "batch",
        "route",
    },
)


@dataclass(frozen=True)
class NamingTemplate:
    """Ordered template for canonical segment composition."""

    segments: tuple[str, ...]
    separator: str = "_"
    required_segments: tuple[str, ...] | None = None


@dataclass(frozen=True)
class NamingConstraints:
    """Constraints applied to segment and final name validation."""

    max_length: int = 255
    allowed_segment_pattern: str = r"[A-Za-z0-9_-]+"


@dataclass(frozen=True)
class NamingCompositionResult:
    """Composed canonical name plus deterministic diagnostics."""

    canonical_name: str
    segments: tuple[tuple[str, str], ...]
    normalized_alternate: str
    identity_hash: str


def _validate_template(template: NamingTemplate) -> tuple[str, ...]:
    if not template.separator:
        raise NamingTemplateError("Template separator must be non-empty.")
    if not template.segments:
        raise NamingTemplateError("Template must contain at least one segment.")

    for segment in template.segments:
        if segment not in KNOWN_SEGMENTS:
            raise NamingTemplateError(
                f"Unknown segment placeholder '{segment}' in naming template.",
            )

    required = tuple(template.required_segments or template.segments)
    for segment in required:
        if segment not in template.segments:
            raise NamingTemplateError(
                "Required segment definitions must exist in template segments.",
            )
    return required


def _validate_segment_value(
    *,
    segment_name: str,
    value: str,
    constraints: NamingConstraints,
    pattern: re.Pattern[str],
) -> None:
    if not value:
        raise NamingMissingSegmentError(
            f"Missing required segment token for '{segment_name}'.",
        )
    if not pattern.fullmatch(value):
        raise NamingSegmentValidationError(
            f"Segment '{segment_name}' contains invalid characters.",
        )


def _stable_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:16]


def compose_name(
    *,
    template: NamingTemplate,
    segment_values: Mapping[str, str],
    constraints: NamingConstraints,
) -> NamingCompositionResult:
    """Compose canonical name from template and validated segment values."""
    required_segments = _validate_template(template)
    pattern = re.compile(constraints.allowed_segment_pattern)

    ordered: list[tuple[str, str]] = []
    required_set = set(required_segments)
    for segment in template.segments:
        value = segment_values.get(segment)
        if value is None and segment in required_set:
            raise NamingMissingSegmentError(
                f"Missing required segment token for '{segment}'.",
            )
        if value is None:
            continue

        _validate_segment_value(
            segment_name=segment,
            value=value,
            constraints=constraints,
            pattern=pattern,
        )
        ordered.append((segment, value))

    composed = template.separator.join(value for _, value in ordered)
    if len(composed) > constraints.max_length:
        raise NamingLengthError(
            "Composed name exceeds configured maximum length constraint.",
        )

    return NamingCompositionResult(
        canonical_name=composed,
        segments=tuple(ordered),
        normalized_alternate=composed.casefold(),
        identity_hash=_stable_hash(composed),
    )


def compose_many(
    *,
    template: NamingTemplate,
    values_list: Sequence[Mapping[str, str]],
    constraints: NamingConstraints,
) -> tuple[NamingCompositionResult, ...]:
    """Compose multiple names deterministically using the same template/constraints."""
    return tuple(
        compose_name(
            template=template,
            segment_values=segment_values,
            constraints=constraints,
        )
        for segment_values in values_list
    )
