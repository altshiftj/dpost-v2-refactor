from __future__ import annotations

from dpost_v2.application.ingestion.policies.error_handling import classify_exception
from dpost_v2.application.ingestion.policies.failure_outcome import (
    FailureOutcomeTypeError,
    FailureTerminalType,
    build_failure_outcome,
)


class _RetryableError(RuntimeError):
    pass


def test_error_handling_default_classification() -> None:
    result = classify_exception(ValueError("boom"), stage_id="persist")

    assert result.stage_id == "persist"
    assert result.reason_code == "value_error"
    assert result.retryable is False


def test_failure_outcome_requires_retry_payload_for_retry_terminal_type() -> None:
    classification = classify_exception(_RetryableError("retry me"), stage_id="persist")

    outcome = build_failure_outcome(
        classification=classification,
        terminal_type=FailureTerminalType.RETRY,
        retry_plan={"delay_seconds": 1.0, "next_attempt": 2},
    )
    assert outcome.terminal_type is FailureTerminalType.RETRY

    try:
        build_failure_outcome(
            classification=classification,
            terminal_type=FailureTerminalType.RETRY,
            retry_plan=None,
        )
    except FailureOutcomeTypeError:
        pass
    else:
        raise AssertionError("expected FailureOutcomeTypeError")
