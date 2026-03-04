from __future__ import annotations

from dpost_v2.application.ingestion.policies.force_path import (
    ForcePathDecisionType,
    evaluate_force_path,
)


def test_force_path_ignores_when_override_not_provided() -> None:
    decision = evaluate_force_path(
        override_path=None,
        allowed_roots=("C:/dest",),
        default_target="C:/dest/default.txt",
    )

    assert decision.decision_type is ForcePathDecisionType.IGNORE_OVERRIDE
    assert decision.normalized_path == "C:/dest/default.txt"


def test_force_path_rejects_root_escape() -> None:
    decision = evaluate_force_path(
        override_path="C:/other/out.txt",
        allowed_roots=("C:/dest",),
        default_target="C:/dest/default.txt",
    )

    assert decision.decision_type is ForcePathDecisionType.REJECT_OVERRIDE
    assert decision.reason_code == "outside_allowed_roots"


def test_force_path_applies_safe_override() -> None:
    decision = evaluate_force_path(
        override_path="C:/dest/a/b.txt",
        allowed_roots=("C:/dest",),
        default_target="C:/dest/default.txt",
    )

    assert decision.decision_type is ForcePathDecisionType.APPLY_OVERRIDE
    assert decision.normalized_path == "C:/dest/a/b.txt"
