"""Unit tests for rename retry prompt policy decisions."""

from __future__ import annotations

from pathlib import Path

from dpost.application.interactions import DialogPrompts, WarningMessages
from dpost.application.processing.rename_retry_policy import build_rename_retry_prompt
from dpost.domain.processing.models import (
    ProcessingCandidate,
    RouteContext,
    RoutingDecision,
)
from tests.helpers.fake_processor import DummyProcessor


def _candidate(*, prefix: str, device) -> ProcessingCandidate:
    """Build a minimal processing candidate for route-policy tests."""
    path = Path(f"C:/watch/{prefix}.txt")
    return ProcessingCandidate(
        original_path=path,
        effective_path=path,
        prefix=prefix,
        extension=".txt",
        processor=DummyProcessor(),
        device=device,
        preprocessed_path=None,
    )


def test_build_rename_retry_prompt_unappendable_returns_warning_policy(
    config_service,
) -> None:
    """Unappendable routes should provide warning metadata and contextual prompt."""
    candidate = _candidate(prefix="bad", device=config_service.devices[0])
    context = RouteContext(candidate, "abc-ipat-sample", None, RoutingDecision.UNAPPENDABLE)

    policy = build_rename_retry_prompt(context)

    assert policy.next_prefix == "abc-ipat-sample"
    assert policy.contextual_reason == DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
        record_id="abc-ipat-sample"
    )
    assert policy.warning_title == WarningMessages.INVALID_RECORD
    assert policy.warning_message == WarningMessages.INVALID_RECORD_DETAILS


def test_build_rename_retry_prompt_default_returns_candidate_prefix(config_service) -> None:
    """Non-unappendable routes should retry with candidate prefix and no warning."""
    candidate = _candidate(prefix="rename-me", device=config_service.devices[0])
    context = RouteContext(candidate, "ignored-sanitized", None, RoutingDecision.REQUIRE_RENAME)

    policy = build_rename_retry_prompt(context)

    assert policy.next_prefix == "rename-me"
    assert policy.contextual_reason is None
    assert policy.warning_title is None
    assert policy.warning_message is None
