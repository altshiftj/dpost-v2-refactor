"""Unit tests for V2 domain routing rules."""

from __future__ import annotations

import pytest

from dpost_v2.domain.routing.rules import (
    RouteDecisionKind,
    RouteRule,
    RoutingDestinationValidationError,
    RoutingRuleAmbiguityError,
    RoutingRuleConfigurationError,
    RoutingRuleNotFoundError,
    decide_route,
    route_rule_sort_key,
)


def test_decide_route_uses_highest_priority_matching_rule() -> None:
    """Route decisions must prefer the highest-priority matching rule."""
    rules = (
        RouteRule(
            rule_id="generic_prod",
            priority=10,
            predicates={"profile": "prod"},
            destinations=("GEN", "DEST"),
        ),
        RouteRule(
            rule_id="rheo_prod",
            priority=20,
            predicates={"profile": "prod", "device_family": "rheometer"},
            destinations=("RHE", "DEST"),
        ),
    )

    decision = decide_route(
        route_facts={"profile": "prod", "device_family": "rheometer"},
        rules=rules,
    )

    assert decision.kind is RouteDecisionKind.MATCHED
    assert decision.destinations == ("RHE", "DEST")
    assert decision.matched_rule_id == "rheo_prod"


def test_decide_route_rejects_ambiguous_top_priority_matches() -> None:
    """Raise when equal-priority route rules match the same facts."""
    rules = (
        RouteRule(
            rule_id="rule_a",
            priority=100,
            predicates={"profile": "prod"},
            destinations=("A",),
        ),
        RouteRule(
            rule_id="rule_b",
            priority=100,
            predicates={"profile": "prod"},
            destinations=("B",),
        ),
    )

    with pytest.raises(RoutingRuleAmbiguityError):
        decide_route(route_facts={"profile": "prod"}, rules=rules)


def test_decide_route_uses_default_destination_when_no_match() -> None:
    """Apply default route deterministically when no explicit rule matches."""
    decision = decide_route(
        route_facts={"profile": "qa"},
        rules=(),
        default_destinations=("DEFAULT",),
    )

    assert decision.kind is RouteDecisionKind.DEFAULTED
    assert decision.destinations == ("DEFAULT",)
    assert decision.matched_rule_id is None


def test_decide_route_raises_when_no_match_and_no_default() -> None:
    """Raise typed not-found error for unmatched route facts without fallback."""
    with pytest.raises(RoutingRuleNotFoundError):
        decide_route(route_facts={"profile": "qa"}, rules=())


def test_decide_route_rejects_invalid_destination_tokens() -> None:
    """Reject destinations violating token-format constraints."""
    rules = (
        RouteRule(
            rule_id="invalid_dest",
            priority=10,
            predicates={"profile": "prod"},
            destinations=("DEST/INVALID",),
        ),
    )
    with pytest.raises(RoutingDestinationValidationError):
        decide_route(route_facts={"profile": "prod"}, rules=rules)


def test_decide_route_rejects_invalid_rule_configuration() -> None:
    """Reject malformed rule sets before rule evaluation begins."""
    rules = (
        RouteRule(
            rule_id="dup",
            priority=10,
            predicates={"profile": "prod"},
            destinations=("A",),
        ),
        RouteRule(
            rule_id="dup",
            priority=20,
            predicates={"profile": "prod", "device_family": "rheometer"},
            destinations=("B",),
        ),
    )
    with pytest.raises(RoutingRuleConfigurationError):
        decide_route(
            route_facts={"profile": "prod", "device_family": "rheometer"},
            rules=rules,
        )


def test_route_rule_sort_key_is_deterministic() -> None:
    """Comparator helper should produce stable deterministic ordering keys."""
    rule = RouteRule(
        rule_id="rheo_prod",
        priority=20,
        predicates={"profile": "prod"},
        destinations=("RHE",),
    )
    assert route_rule_sort_key(rule) == (-20, "rheo_prod")
