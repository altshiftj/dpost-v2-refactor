"""Unit and integration tests for V2 canonical naming policy."""

from __future__ import annotations

import pytest

from dpost_v2.domain.naming.identifiers import IdentifierRules, parse_identifier
from dpost_v2.domain.naming.policy import (
    NamingConstraints,
    NamingLengthError,
    NamingMissingSegmentError,
    NamingSegmentValidationError,
    NamingTemplate,
    NamingTemplateError,
    compose_name,
)
from dpost_v2.domain.naming.prefix_policy import PrefixRule, derive_prefix


def test_compose_name_respects_template_segment_order() -> None:
    """Compose canonical names following exact template ordering."""
    template = NamingTemplate(
        segments=("prefix", "identifier", "timestamp"),
        separator="_",
    )
    constraints = NamingConstraints(max_length=64)

    result = compose_name(
        template=template,
        segment_values={
            "prefix": "RHE",
            "identifier": "mat_rheo_20260304",
            "timestamp": "20260304T101500",
        },
        constraints=constraints,
    )

    assert result.canonical_name == "RHE_mat_rheo_20260304_20260304T101500"
    assert tuple(name for name, _ in result.segments) == (
        "prefix",
        "identifier",
        "timestamp",
    )


def test_compose_name_rejects_missing_required_segment() -> None:
    """Raise when required template segments are absent from inputs."""
    template = NamingTemplate(
        segments=("prefix", "identifier"),
        separator="-",
        required_segments=("prefix", "identifier"),
    )

    with pytest.raises(NamingMissingSegmentError):
        compose_name(
            template=template,
            segment_values={"prefix": "RHE"},
            constraints=NamingConstraints(max_length=64),
        )


def test_compose_name_rejects_invalid_segment_characters() -> None:
    """Reject segment values that violate configured character constraints."""
    template = NamingTemplate(segments=("prefix", "identifier"), separator="-")

    with pytest.raises(NamingSegmentValidationError):
        compose_name(
            template=template,
            segment_values={"prefix": "RHE", "identifier": "bad!token"},
            constraints=NamingConstraints(max_length=64),
        )


def test_compose_name_rejects_unknown_template_placeholder() -> None:
    """Reject templates that reference unknown placeholders."""
    template = NamingTemplate(segments=("prefix", "unknown_slot"), separator="-")
    with pytest.raises(NamingTemplateError):
        compose_name(
            template=template,
            segment_values={"prefix": "RHE", "unknown_slot": "X"},
            constraints=NamingConstraints(max_length=64),
        )


def test_compose_name_rejects_values_exceeding_max_length() -> None:
    """Reject names that exceed max-length constraints."""
    template = NamingTemplate(segments=("prefix", "identifier"), separator="-")
    with pytest.raises(NamingLengthError):
        compose_name(
            template=template,
            segment_values={"prefix": "RHE", "identifier": "x" * 50},
            constraints=NamingConstraints(max_length=10),
        )


def test_compose_name_is_deterministic_for_identical_inputs() -> None:
    """Equivalent domain inputs should produce identical name/hash outputs."""
    template = NamingTemplate(
        segments=("prefix", "identifier", "route"),
        separator="_",
    )
    constraints = NamingConstraints(max_length=128)
    values = {"prefix": "RHE", "identifier": "abc_123", "route": "dest01"}

    result_a = compose_name(
        template=template, segment_values=values, constraints=constraints
    )
    result_b = compose_name(
        template=template, segment_values=values, constraints=constraints
    )

    assert result_a.canonical_name == result_b.canonical_name
    assert result_a.identity_hash == result_b.identity_hash


def test_naming_policy_integration_with_identifier_and_prefix_domains() -> None:
    """Use identifier parse + prefix derivation outputs to compose canonical names."""
    parsed = parse_identifier(
        "MAT-RHEO-20260304",
        rules=IdentifierRules(
            primary_separator="-",
            min_tokens=3,
            max_tokens=3,
            casefold=True,
        ),
    )
    prefix = derive_prefix(
        attributes={"device_family": "rheometer", "profile": "prod"},
        rules=(
            PrefixRule(
                rule_id="prod_rheo",
                priority=10,
                conditions={"device_family": "rheometer", "profile": "prod"},
                prefix="RHE",
            ),
        ),
    )

    template = NamingTemplate(segments=("prefix", "identifier"), separator="-")
    result = compose_name(
        template=template,
        segment_values={"prefix": prefix.token or "", "identifier": parsed.canonical},
        constraints=NamingConstraints(max_length=64),
    )

    assert result.canonical_name == "RHE-mat-rheo-20260304"
