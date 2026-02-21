"""Unit coverage for domain routing decision policy."""

from __future__ import annotations

from dataclasses import dataclass, field

from dpost.domain.processing.models import RoutingDecision
from dpost.domain.processing.routing import determine_routing_decision
from dpost.domain.records.local_record import LocalRecord


@dataclass
class StubAppendabilityPolicy:
    """Track appendability checks and return a fixed result."""

    appendable: bool
    calls: list[tuple[LocalRecord, str, str]] = field(default_factory=list)

    def is_appendable(
        self,
        record: LocalRecord,
        filename_prefix: str,
        extension: str,
    ) -> bool:
        """Return the configured appendability response and record invocation."""
        self.calls.append((record, filename_prefix, extension))
        return self.appendable


def test_determine_routing_decision_accepts_new_valid_item() -> None:
    """Accept valid names when there is no existing record yet."""
    policy = StubAppendabilityPolicy(appendable=False)

    decision = determine_routing_decision(
        record=None,
        is_valid_format=True,
        filename_prefix="abc-ipat-sample",
        extension=".txt",
        processor=policy,
    )

    assert decision is RoutingDecision.ACCEPT
    assert policy.calls == []


def test_determine_routing_decision_requires_rename_for_invalid_new_item() -> None:
    """Require rename for invalid names even when no record exists."""
    policy = StubAppendabilityPolicy(appendable=True)

    decision = determine_routing_decision(
        record=None,
        is_valid_format=False,
        filename_prefix="invalid",
        extension=".txt",
        processor=policy,
    )

    assert decision is RoutingDecision.REQUIRE_RENAME
    assert policy.calls == []


def test_determine_routing_decision_requires_rename_for_invalid_existing_record() -> None:
    """Prioritize name validity over appendability for existing records."""
    policy = StubAppendabilityPolicy(appendable=True)
    record = LocalRecord(identifier="dev-user-org-sample_1")

    decision = determine_routing_decision(
        record=record,
        is_valid_format=False,
        filename_prefix="bad-prefix",
        extension=".csv",
        processor=policy,
    )

    assert decision is RoutingDecision.REQUIRE_RENAME
    assert policy.calls == []


def test_determine_routing_decision_accepts_appendable_existing_record() -> None:
    """Accept valid items when processor confirms appendability."""
    policy = StubAppendabilityPolicy(appendable=True)
    record = LocalRecord(identifier="dev-user-org-sample_1")

    decision = determine_routing_decision(
        record=record,
        is_valid_format=True,
        filename_prefix="dev-user-org-sample_1",
        extension=".ngb",
        processor=policy,
    )

    assert decision is RoutingDecision.ACCEPT
    assert policy.calls == [(record, "dev-user-org-sample_1", ".ngb")]


def test_determine_routing_decision_rejects_unappendable_existing_record() -> None:
    """Return UNAPPENDABLE when an existing valid record cannot append the file."""
    policy = StubAppendabilityPolicy(appendable=False)
    record = LocalRecord(identifier="dev-user-org-sample_1")

    decision = determine_routing_decision(
        record=record,
        is_valid_format=True,
        filename_prefix="dev-user-org-sample_1",
        extension=".tif",
        processor=policy,
    )

    assert decision is RoutingDecision.UNAPPENDABLE
    assert policy.calls == [(record, "dev-user-org-sample_1", ".tif")]
