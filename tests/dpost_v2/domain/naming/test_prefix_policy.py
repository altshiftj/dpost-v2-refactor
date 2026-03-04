"""Unit tests for V2 domain prefix derivation policy."""

from __future__ import annotations

import pytest

from dpost_v2.domain.naming.prefix_policy import (
    PrefixDecisionKind,
    PrefixDerivationNotFoundError,
    PrefixRule,
    PrefixRuleAmbiguityError,
    PrefixRuleConfigurationError,
    PrefixTokenFormatError,
    derive_prefix,
)


def test_derive_prefix_uses_highest_priority_matching_rule() -> None:
    """Select the highest-priority rule among all matches deterministically."""
    rules = (
        PrefixRule(
            rule_id="generic_prod",
            priority=10,
            conditions={"profile": "prod"},
            prefix="GEN",
        ),
        PrefixRule(
            rule_id="rheo_prod",
            priority=20,
            conditions={"profile": "prod", "device_family": "rheometer"},
            prefix="RHE",
        ),
    )

    decision = derive_prefix(
        attributes={"profile": "prod", "device_family": "rheometer"},
        rules=rules,
    )

    assert decision.kind is PrefixDecisionKind.DERIVED
    assert decision.token == "RHE"
    assert decision.matched_rule_id == "rheo_prod"


def test_derive_prefix_rejects_ambiguous_top_priority_match() -> None:
    """Raise when multiple highest-priority rules match the same attributes."""
    rules = (
        PrefixRule(
            rule_id="rule_a",
            priority=50,
            conditions={"profile": "prod"},
            prefix="AAA",
        ),
        PrefixRule(
            rule_id="rule_b",
            priority=50,
            conditions={"profile": "prod"},
            prefix="BBB",
        ),
    )

    with pytest.raises(PrefixRuleAmbiguityError):
        derive_prefix(attributes={"profile": "prod"}, rules=rules)


def test_derive_prefix_uses_fallback_when_no_rule_matches() -> None:
    """Return fallback decision when rule evaluation yields no match."""
    decision = derive_prefix(
        attributes={"profile": "qa"},
        rules=(),
        fallback_prefix="DFLT",
    )

    assert decision.kind is PrefixDecisionKind.FALLBACK
    assert decision.token == "DFLT"
    assert decision.matched_rule_id is None


def test_derive_prefix_raises_when_no_rule_and_no_fallback() -> None:
    """Raise typed not-found error for unmatched attributes without fallback."""
    with pytest.raises(PrefixDerivationNotFoundError):
        derive_prefix(attributes={"profile": "qa"}, rules=())


def test_derive_prefix_rejects_invalid_derived_token_format() -> None:
    """Reject derived tokens that violate prefix-token format constraints."""
    rules = (
        PrefixRule(
            rule_id="bad_format",
            priority=10,
            conditions={"profile": "prod"},
            prefix="BAD-TOKEN!",
        ),
    )

    with pytest.raises(PrefixTokenFormatError):
        derive_prefix(attributes={"profile": "prod"}, rules=rules)


def test_derive_prefix_rejects_invalid_rule_configuration() -> None:
    """Reject malformed/duplicate rule config with typed configuration error."""
    rules = (
        PrefixRule(
            rule_id="dup",
            priority=10,
            conditions={"profile": "prod"},
            prefix="ONE",
        ),
        PrefixRule(
            rule_id="dup",
            priority=20,
            conditions={"profile": "prod", "device_family": "rheometer"},
            prefix="TWO",
        ),
    )

    with pytest.raises(PrefixRuleConfigurationError):
        derive_prefix(
            attributes={"profile": "prod", "device_family": "rheometer"},
            rules=rules,
        )
