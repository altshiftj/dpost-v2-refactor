"""Contract tests for V2 runtime and processing context models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from dpost_v2.application.contracts.context import (
    ContextValidationError,
    InvalidCandidateContextError,
    ProcessingContext,
    RetryStateError,
    RuntimeContext,
    UnsupportedRuntimeModeError,
    validate_processing_context,
    validate_runtime_context,
)


def _settings(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "mode": "  Headless ",
        "profile": "  Default ",
        "session_id": "session-1",
        "event_id": "runtime-event-1",
        "trace_id": "trace-1",
    }
    values.update(overrides)
    return values


def _dependency_ids(**overrides: str) -> dict[str, str]:
    values = {"clock": "clock-1", "ui": "ui-1", "sync": "sync-1"}
    values.update(overrides)
    return values


def test_runtime_context_from_settings_normalizes_tokens_and_is_immutable() -> None:
    context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )

    assert context.mode == "headless"
    assert context.profile == "default"
    assert context.session_id == "session-1"
    assert context.event_id == "runtime-event-1"
    assert context.trace_id == "trace-1"
    assert context.dependency_ids["clock"] == "clock-1"

    with pytest.raises(FrozenInstanceError):
        context.mode = "desktop"


def test_runtime_context_from_settings_rejects_missing_required_fields() -> None:
    with pytest.raises(ContextValidationError, match="session_id"):
        RuntimeContext.from_settings(
            settings=_settings(session_id=""),
            dependency_ids=_dependency_ids(),
        )


def test_runtime_context_from_settings_rejects_unsupported_mode() -> None:
    with pytest.raises(UnsupportedRuntimeModeError):
        RuntimeContext.from_settings(
            settings=_settings(mode="invalid-mode"),
            dependency_ids=_dependency_ids(),
        )


def test_runtime_context_from_settings_rejects_invalid_mode_profile_combination() -> (
    None
):
    with pytest.raises(UnsupportedRuntimeModeError, match="profile"):
        RuntimeContext.from_settings(
            settings=_settings(
                profile="lab-a",
                allowed_profiles_by_mode={"headless": ("default",)},
            ),
            dependency_ids=_dependency_ids(),
        )


def test_processing_context_for_candidate_captures_event_metadata() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )
    observed_at = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)

    context = ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": observed_at,
            "event_id": "evt-100",
            "trace_id": "trace-100",
            "force_paths": ("D:/incoming/aux.bin",),
        },
    )

    assert context.runtime_context is runtime_context
    assert context.source_path == "D:/incoming/file.tif"
    assert context.event_type == "created"
    assert context.observed_at == observed_at
    assert context.event_id == "evt-100"
    assert context.trace_id == "trace-100"
    assert context.retry_attempt == 0
    assert context.force_paths == ("D:/incoming/aux.bin",)


def test_processing_context_for_candidate_uses_runtime_correlation_defaults() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(event_id="runtime-evt", trace_id="runtime-trace"),
        dependency_ids=_dependency_ids(),
    )

    context = ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "modified",
            "observed_at": datetime(2026, 3, 4, tzinfo=UTC),
        },
    )

    assert context.event_id == "runtime-evt"
    assert context.trace_id == "runtime-trace"


def test_processing_context_force_paths_are_normalized_to_immutable_tuple() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )
    context = ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, tzinfo=UTC),
            "force_paths": [" D:/incoming/aux_a.bin ", "D:/incoming/aux_b.bin"],
        },
    )

    assert context.force_paths == ("D:/incoming/aux_a.bin", "D:/incoming/aux_b.bin")
    assert isinstance(context.force_paths, tuple)


def test_processing_context_for_candidate_rejects_invalid_path_token() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )

    with pytest.raises(InvalidCandidateContextError):
        ProcessingContext.for_candidate(
            runtime_context=runtime_context,
            candidate_event={
                "source_path": "bad\0path",
                "event_type": "created",
                "observed_at": datetime(2026, 3, 4, tzinfo=UTC),
            },
        )


def test_processing_context_with_retry_enforces_monotonic_attempts() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )
    context = ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, tzinfo=UTC),
        },
    )

    retry_context = context.with_retry(attempt_index=1, delay_seconds=2.5)

    assert retry_context.retry_attempt == 1
    assert retry_context.retry_delay_seconds == pytest.approx(2.5)
    assert retry_context.source_path == context.source_path
    assert retry_context.runtime_context is context.runtime_context

    with pytest.raises(RetryStateError):
        retry_context.with_retry(attempt_index=0, delay_seconds=1.0)

    with pytest.raises(RetryStateError):
        retry_context.with_retry(attempt_index=1, delay_seconds=-0.1)


def test_processing_context_clone_helpers_preserve_core_invariants() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )
    context = ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, tzinfo=UTC),
            "force_paths": ("D:/incoming/aux.bin",),
        },
    )

    failure = context.with_failure("  stage_error ")
    routed = failure.with_route("  route:rename ")

    assert failure.failure_reason == "stage_error"
    assert routed.route_hint == "route:rename"
    assert routed.source_path == context.source_path
    assert routed.force_paths == context.force_paths
    assert routed.runtime_context is context.runtime_context


def test_context_validation_helpers_reject_invalid_instances() -> None:
    runtime_context = RuntimeContext.from_settings(
        settings=_settings(),
        dependency_ids=_dependency_ids(),
    )
    processing_context = ProcessingContext.for_candidate(
        runtime_context=runtime_context,
        candidate_event={
            "source_path": "D:/incoming/file.tif",
            "event_type": "created",
            "observed_at": datetime(2026, 3, 4, tzinfo=UTC),
        },
    )

    assert validate_runtime_context(runtime_context) is runtime_context
    assert validate_processing_context(processing_context) is processing_context

    with pytest.raises(ContextValidationError):
        validate_runtime_context(
            RuntimeContext.from_settings(
                settings=_settings(trace_id=""),
                dependency_ids=_dependency_ids(),
            )
        )

    with pytest.raises(ContextValidationError):
        validate_processing_context(object())  # type: ignore[arg-type]
