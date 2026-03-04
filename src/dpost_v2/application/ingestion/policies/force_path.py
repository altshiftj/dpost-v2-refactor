from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import PurePath
from typing import Callable, Mapping


class ForcePathDecisionType(StrEnum):
    """Force-path policy decision classes."""

    APPLY_OVERRIDE = "apply_override"
    IGNORE_OVERRIDE = "ignore_override"
    REJECT_OVERRIDE = "reject_override"


@dataclass(frozen=True, slots=True)
class ForcePathDecision:
    """Normalized force-path policy decision payload."""

    decision_type: ForcePathDecisionType
    normalized_path: str | None
    reason_code: str
    diagnostics: Mapping[str, object] = field(default_factory=dict)


def _normalize(path_value: str) -> str:
    return str(PurePath(path_value)).replace("\\", "/")


def _is_under_root(path_value: str, root: str) -> bool:
    normalized_path = _normalize(path_value).lower().rstrip("/")
    normalized_root = _normalize(root).lower().rstrip("/")
    return normalized_path == normalized_root or normalized_path.startswith(
        f"{normalized_root}/"
    )


def evaluate_force_path(
    *,
    override_path: str | None,
    allowed_roots: tuple[str, ...],
    default_target: str,
    conflict_probe: Callable[[str], bool] | None = None,
) -> ForcePathDecision:
    """Evaluate optional force-path override against path safety constraints."""
    fallback_target = _normalize(default_target)
    if override_path is None or not str(override_path).strip():
        return ForcePathDecision(
            decision_type=ForcePathDecisionType.IGNORE_OVERRIDE,
            normalized_path=fallback_target,
            reason_code="override_not_provided",
        )

    normalized_override = _normalize(str(override_path))
    if not any(_is_under_root(normalized_override, root) for root in allowed_roots):
        return ForcePathDecision(
            decision_type=ForcePathDecisionType.REJECT_OVERRIDE,
            normalized_path=None,
            reason_code="outside_allowed_roots",
        )

    if conflict_probe is not None and conflict_probe(normalized_override):
        return ForcePathDecision(
            decision_type=ForcePathDecisionType.REJECT_OVERRIDE,
            normalized_path=None,
            reason_code="override_conflict",
        )

    return ForcePathDecision(
        decision_type=ForcePathDecisionType.APPLY_OVERRIDE,
        normalized_path=normalized_override,
        reason_code="override_applied",
    )
