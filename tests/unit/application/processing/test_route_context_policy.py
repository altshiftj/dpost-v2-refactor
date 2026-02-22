"""Unit tests for route-context construction policy helpers."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.route_context_policy import build_route_context
from dpost.domain.processing.models import (
    ProcessingCandidate,
    RouteContext,
    RoutingDecision,
)
from dpost.domain.records.local_record import LocalRecord
from tests.helpers.fake_processor import DummyProcessor


def test_build_route_context_delegates_to_decision_policy(config_service) -> None:
    """Pass lookup/candidate values to the decision function and wrap RouteContext."""
    candidate = ProcessingCandidate(
        original_path=Path("C:/watch/raw.txt"),
        effective_path=Path("C:/watch/raw.txt"),
        prefix="Raw-Prefix",
        extension=".txt",
        processor=DummyProcessor(),
        device=config_service.devices[0],
        preprocessed_path=None,
    )
    record = LocalRecord(identifier="dev-user-inst-sample")
    calls: list[tuple[object, ...]] = []

    def fake_decide(existing_record, is_valid_format, prefix, extension, processor):
        calls.append((existing_record, is_valid_format, prefix, extension, processor))
        return RoutingDecision.UNAPPENDABLE

    context = build_route_context(
        candidate,
        "sanitized-prefix",
        record,
        True,
        determine_routing_decision_fn=fake_decide,
    )

    assert context == RouteContext(
        candidate,
        "sanitized-prefix",
        record,
        RoutingDecision.UNAPPENDABLE,
    )
    assert calls == [
        (record, True, "Raw-Prefix", ".txt", candidate.processor),
    ]
