"""Prefix derivation rules for V2 naming domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Collection, Mapping, Sequence


class PrefixPolicyError(ValueError):
    """Base class for prefix policy errors."""


class PrefixDerivationNotFoundError(PrefixPolicyError):
    """Raised when no rule matches and no fallback prefix is configured."""


class PrefixTokenFormatError(PrefixPolicyError):
    """Raised when derived/fallback prefix violates format constraints."""


class PrefixRuleAmbiguityError(PrefixPolicyError):
    """Raised when multiple top-priority rules match the same attributes."""


class PrefixRuleConfigurationError(PrefixPolicyError):
    """Raised when prefix rules are malformed or contradictory."""


class PrefixDecisionKind(str, Enum):
    """Prefix decision categories exposed to downstream naming policy."""

    DERIVED = "derived"
    FALLBACK = "fallback"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PrefixRule:
    """Predicate-based rule that may derive a prefix token."""

    rule_id: str
    priority: int
    conditions: Mapping[str, str | Collection[str]]
    prefix: str


@dataclass(frozen=True)
class PrefixDecision:
    """Deterministic prefix decision and diagnostics payload."""

    kind: PrefixDecisionKind
    token: str | None
    matched_rule_id: str | None
    diagnostics: tuple[str, ...]


def _is_collection_value(value: object) -> bool:
    return isinstance(value, Collection) and not isinstance(value, str)


def _validate_rule(rule: PrefixRule, seen_ids: set[str]) -> None:
    if not rule.rule_id:
        raise PrefixRuleConfigurationError("Rule id must be non-empty.")
    if rule.rule_id in seen_ids:
        raise PrefixRuleConfigurationError("Rule ids must be unique.")
    seen_ids.add(rule.rule_id)

    if not isinstance(rule.priority, int):
        raise PrefixRuleConfigurationError("Rule priority must be an integer.")
    if not rule.conditions:
        raise PrefixRuleConfigurationError("Rule conditions must be non-empty.")

    for key, expected in rule.conditions.items():
        if not key:
            raise PrefixRuleConfigurationError("Condition keys must be non-empty.")
        if _is_collection_value(expected):
            values = tuple(str(value) for value in expected)
            if not values:
                raise PrefixRuleConfigurationError(
                    "Collection condition values must be non-empty.",
                )


def _validate_rules(rules: Sequence[PrefixRule]) -> None:
    seen_ids: set[str] = set()
    for rule in rules:
        _validate_rule(rule, seen_ids)


def _matches_rule(
    attributes: Mapping[str, str],
    rule: PrefixRule,
) -> bool:
    for key, expected in rule.conditions.items():
        actual = attributes.get(key)
        if _is_collection_value(expected):
            expected_values = {str(value) for value in expected}
            if actual not in expected_values:
                return False
            continue
        if actual != str(expected):
            return False
    return True


def _validate_token(token: str, token_pattern: re.Pattern[str]) -> None:
    if not token_pattern.fullmatch(token):
        raise PrefixTokenFormatError(
            f"Derived prefix '{token}' violates configured token format.",
        )


def derive_prefix(
    *,
    attributes: Mapping[str, str],
    rules: Sequence[PrefixRule],
    fallback_prefix: str | None = None,
    token_pattern: str = r"[A-Za-z0-9_]+",
) -> PrefixDecision:
    """Derive prefix token via deterministic rule evaluation and fallback policy."""
    _validate_rules(rules)
    compiled_pattern = re.compile(token_pattern)

    ordered_rules = sorted(rules, key=lambda rule: (-rule.priority, rule.rule_id))
    matching_rules = [rule for rule in ordered_rules if _matches_rule(attributes, rule)]

    if matching_rules:
        top_priority = matching_rules[0].priority
        top_matches = [rule for rule in matching_rules if rule.priority == top_priority]
        if len(top_matches) > 1:
            raise PrefixRuleAmbiguityError(
                "Multiple matching prefix rules share the same top priority.",
            )

        selected = top_matches[0]
        _validate_token(selected.prefix, compiled_pattern)
        return PrefixDecision(
            kind=PrefixDecisionKind.DERIVED,
            token=selected.prefix,
            matched_rule_id=selected.rule_id,
            diagnostics=tuple(rule.rule_id for rule in matching_rules),
        )

    if fallback_prefix is None:
        raise PrefixDerivationNotFoundError(
            "No prefix rule matched and no fallback prefix was configured.",
        )

    _validate_token(fallback_prefix, compiled_pattern)
    return PrefixDecision(
        kind=PrefixDecisionKind.FALLBACK,
        token=fallback_prefix,
        matched_rule_id=None,
        diagnostics=("fallback",),
    )
