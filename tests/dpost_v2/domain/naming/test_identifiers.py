"""Unit tests for V2 domain identifier parsing/composition rules."""

from __future__ import annotations

import pytest

from dpost_v2.domain.naming.identifiers import (
    IdentifierCharacterError,
    IdentifierEmptyError,
    IdentifierRules,
    IdentifierSeparatorError,
    IdentifierTokenCountError,
    compose_identifier,
    parse_identifier,
    validate_identifier,
)


def test_parse_identifier_supports_alternate_separator_and_canonicalizes() -> None:
    """Parse accepted alternate separators and compose canonical primary-separator IDs."""
    rules = IdentifierRules(
        primary_separator="-",
        alternate_separators=("_",),
        min_tokens=3,
        max_tokens=3,
        casefold=True,
    )

    parsed = parse_identifier("MAT_Device_20260304", rules=rules)

    assert parsed.tokens == ("mat", "device", "20260304")
    assert parsed.canonical == "mat-device-20260304"


def test_parse_then_compose_preserves_canonical_round_trip() -> None:
    """Compose(parse(x)) should always return canonical identifier form."""
    rules = IdentifierRules(
        primary_separator="-",
        alternate_separators=("_",),
        min_tokens=3,
        max_tokens=3,
        casefold=True,
    )

    parsed = parse_identifier("MAT-device_20260304", rules=rules)
    composed = compose_identifier(parsed.tokens, rules=rules)

    assert composed == parsed.canonical
    assert composed == "mat-device-20260304"


def test_parse_identifier_rejects_empty_input() -> None:
    """Reject empty identifiers with a typed domain error."""
    rules = IdentifierRules()
    with pytest.raises(IdentifierEmptyError):
        parse_identifier("   ", rules=rules)


def test_parse_identifier_rejects_illegal_token_characters() -> None:
    """Reject identifiers containing characters outside token constraints."""
    rules = IdentifierRules(min_tokens=3, max_tokens=3)
    with pytest.raises(IdentifierCharacterError):
        parse_identifier("mat-dev!ce-20260304", rules=rules)


def test_parse_identifier_rejects_invalid_token_count() -> None:
    """Reject identifiers outside configured token-count bounds."""
    rules = IdentifierRules(min_tokens=3, max_tokens=3)
    with pytest.raises(IdentifierTokenCountError):
        parse_identifier("mat-device", rules=rules)


def test_parse_identifier_rejects_invalid_separator_configuration() -> None:
    """Reject invalid separator config before any token parsing runs."""
    rules = IdentifierRules(primary_separator="")
    with pytest.raises(IdentifierSeparatorError):
        parse_identifier("mat-device-20260304", rules=rules)


def test_validate_identifier_returns_structured_invalid_result() -> None:
    """Validation helper should return deterministic invalid reason details."""
    rules = IdentifierRules(min_tokens=3, max_tokens=3)

    validation = validate_identifier("mat-device", rules=rules)

    assert validation.valid is False
    assert validation.error_type == "IdentifierTokenCountError"
    assert "token count" in (validation.reason or "").lower()
