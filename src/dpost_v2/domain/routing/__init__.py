"""Routing domain contracts for V2."""

from dpost_v2.domain.routing.rules import (
    RouteDecision,
    RouteDecisionKind,
    RouteRule,
    RoutingDestinationValidationError,
    RoutingRuleAmbiguityError,
    RoutingRuleConfigurationError,
    RoutingRuleNotFoundError,
    decide_route,
    route_rule_sort_key,
)

__all__ = [
    "RouteDecision",
    "RouteDecisionKind",
    "RouteRule",
    "RoutingDestinationValidationError",
    "RoutingRuleAmbiguityError",
    "RoutingRuleConfigurationError",
    "RoutingRuleNotFoundError",
    "decide_route",
    "route_rule_sort_key",
]
