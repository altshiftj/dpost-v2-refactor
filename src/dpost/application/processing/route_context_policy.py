"""Pure policy helper for constructing processing route contexts."""

from __future__ import annotations

from collections.abc import Callable

from dpost.domain.processing.models import (
    ProcessingCandidate,
    RouteContext,
    RoutingDecision,
)
from dpost.domain.processing.routing import determine_routing_decision
from dpost.domain.records.local_record import LocalRecord


def build_route_context(
    candidate: ProcessingCandidate,
    sanitized_prefix: str,
    existing_record: LocalRecord | None,
    is_valid_format: bool,
    *,
    determine_routing_decision_fn: Callable[..., RoutingDecision] = determine_routing_decision,
) -> RouteContext:
    """Build a route context from lookup results and a candidate artefact."""
    decision = determine_routing_decision_fn(
        existing_record,
        is_valid_format,
        candidate.prefix,
        candidate.extension,
        candidate.processor,
    )
    return RouteContext(candidate, sanitized_prefix, existing_record, decision)
