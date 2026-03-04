"""Deterministic routing rule evaluation for V2 domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Collection, Mapping, Sequence


class RoutingRuleError(ValueError):
    """Base class for routing rule errors."""


class RoutingRuleNotFoundError(RoutingRuleError):
    """Raised when no rule matches and no default route is configured."""


class RoutingRuleAmbiguityError(RoutingRuleError):
    """Raised when multiple top-priority rules match."""


class RoutingRuleConfigurationError(RoutingRuleError):
    """Raised when routing rules are malformed or contradictory."""


class RoutingDestinationValidationError(RoutingRuleError):
    """Raised when a selected destination token is invalid."""


class RouteDecisionKind(str, Enum):
    """Route decision outcomes for domain-level rule evaluation."""

    MATCHED = "matched"
    DEFAULTED = "defaulted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class RouteRule:
    """Rule with predicate map and destination token set."""

    rule_id: str
    priority: int
    predicates: Mapping[str, str | Collection[str]]
    destinations: tuple[str, ...]


@dataclass(frozen=True)
class RouteDecision:
    """Deterministic route decision result plus diagnostics."""

    kind: RouteDecisionKind
    destinations: tuple[str, ...]
    matched_rule_id: str | None
    diagnostics: tuple[str, ...]


def route_rule_sort_key(rule: RouteRule) -> tuple[int, str]:
    """Return comparator key for deterministic priority ordering."""
    return (-rule.priority, rule.rule_id)


def _is_collection_value(value: object) -> bool:
    return isinstance(value, Collection) and not isinstance(value, str)


def _validate_rule(rule: RouteRule, *, seen_ids: set[str]) -> None:
    if not rule.rule_id:
        raise RoutingRuleConfigurationError("Rule id must be non-empty.")
    if rule.rule_id in seen_ids:
        raise RoutingRuleConfigurationError("Rule ids must be unique.")
    seen_ids.add(rule.rule_id)

    if not isinstance(rule.priority, int):
        raise RoutingRuleConfigurationError("Rule priority must be an integer.")
    if not rule.predicates:
        raise RoutingRuleConfigurationError("Rule predicates must be non-empty.")
    if not rule.destinations:
        raise RoutingRuleConfigurationError("Rule destinations must be non-empty.")

    for key, expected in rule.predicates.items():
        if not key:
            raise RoutingRuleConfigurationError("Predicate keys must be non-empty.")
        if _is_collection_value(expected):
            values = tuple(str(value) for value in expected)
            if not values:
                raise RoutingRuleConfigurationError(
                    "Collection predicate values must be non-empty.",
                )


def _validate_destinations(
    destinations: Sequence[str],
    destination_pattern: re.Pattern[str],
) -> tuple[str, ...]:
    validated: list[str] = []
    for destination in destinations:
        if not destination_pattern.fullmatch(destination):
            raise RoutingDestinationValidationError(
                f"Destination token '{destination}' violates allowed format.",
            )
        validated.append(destination)
    return tuple(validated)


def _rule_matches(
    *,
    route_facts: Mapping[str, str],
    rule: RouteRule,
) -> bool:
    for key, expected in rule.predicates.items():
        actual = route_facts.get(key)
        if _is_collection_value(expected):
            expected_values = {str(value) for value in expected}
            if actual not in expected_values:
                return False
            continue
        if actual != str(expected):
            return False
    return True


def decide_route(
    *,
    route_facts: Mapping[str, str],
    rules: Sequence[RouteRule],
    default_destinations: Sequence[str] | None = None,
    destination_pattern: str = r"[A-Za-z0-9_]+",
) -> RouteDecision:
    """Evaluate route facts against rules and return deterministic decision."""
    seen_ids: set[str] = set()
    compiled_destination_pattern = re.compile(destination_pattern)
    for rule in rules:
        _validate_rule(rule, seen_ids=seen_ids)
        _validate_destinations(rule.destinations, compiled_destination_pattern)

    ordered_rules = sorted(rules, key=route_rule_sort_key)
    matches = [rule for rule in ordered_rules if _rule_matches(route_facts=route_facts, rule=rule)]

    if matches:
        top_priority = matches[0].priority
        top_matches = [rule for rule in matches if rule.priority == top_priority]
        if len(top_matches) > 1:
            raise RoutingRuleAmbiguityError(
                "Multiple matching route rules share the same top priority.",
            )
        selected = top_matches[0]
        return RouteDecision(
            kind=RouteDecisionKind.MATCHED,
            destinations=tuple(selected.destinations),
            matched_rule_id=selected.rule_id,
            diagnostics=tuple(rule.rule_id for rule in matches),
        )

    if default_destinations is None:
        raise RoutingRuleNotFoundError(
            "No routing rule matched and no default route was configured.",
        )

    resolved_default = _validate_destinations(
        tuple(default_destinations),
        compiled_destination_pattern,
    )
    return RouteDecision(
        kind=RouteDecisionKind.DEFAULTED,
        destinations=resolved_default,
        matched_rule_id=None,
        diagnostics=("default",),
    )

