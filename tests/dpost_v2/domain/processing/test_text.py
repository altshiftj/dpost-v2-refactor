"""Unit tests for V2 domain text parsing and normalization helpers."""

from __future__ import annotations

import pytest

from dpost_v2.domain.processing.text import (
    TextEncodingError,
    TextHeaderValidationError,
    TextNormalizationPolicy,
    TextParseOptions,
    TextParseStructureError,
    TextRowShapeError,
    normalize_token,
    parse_text_records,
)


def test_normalize_token_is_idempotent() -> None:
    """Applying normalization repeatedly should return identical token output."""
    policy = TextNormalizationPolicy(
        trim_tokens=True,
        collapse_internal_whitespace=True,
        casefold_tokens=True,
    )

    once = normalize_token("  Sample   Name  ", policy=policy)
    twice = normalize_token(once, policy=policy)

    assert once == "sample name"
    assert twice == once


def test_parse_text_records_rejects_missing_required_header() -> None:
    """Reject records missing required headers before row processing."""
    options = TextParseOptions(required_headers=("id", "value"))
    with pytest.raises(TextHeaderValidationError):
        parse_text_records("id,other\n1,2\n", options=options)


def test_parse_text_records_rejects_malformed_quote_structure() -> None:
    """Reject malformed CSV quote/delimiter structure with typed parse error."""
    options = TextParseOptions()
    with pytest.raises(TextParseStructureError):
        parse_text_records('id,value\n"1,2\n', options=options)


def test_parse_text_records_rejects_inconsistent_row_shape_in_strict_mode() -> None:
    """Strict mode should reject row/column count mismatches."""
    options = TextParseOptions(strict_row_shape=True)
    with pytest.raises(TextRowShapeError):
        parse_text_records("id,value\n1,2,3\n", options=options)


def test_parse_text_records_tries_later_encoding_hints() -> None:
    """Decode bytes with later encoding hints when earlier hints fail."""
    payload = "id,value\n1,ÿ\n".encode("latin-1")
    options = TextParseOptions(encoding_hints=("utf-8", "latin-1"))

    result = parse_text_records(payload, options=options)

    assert result.header == ("id", "value")
    assert result.rows == (("1", "ÿ"),)


def test_parse_text_records_rejects_unknown_encoding_hint() -> None:
    """Reject unknown encoding names deterministically."""
    options = TextParseOptions(encoding_hints=("definitely_not_an_encoding",))
    with pytest.raises(TextEncodingError):
        parse_text_records(b"id,value\n1,2\n", options=options)


def test_parse_text_records_collects_warnings_when_not_strict() -> None:
    """Non-strict mode should keep parsing while emitting deterministic warnings."""
    options = TextParseOptions(strict_row_shape=False)

    result = parse_text_records("id,value\n1,2,3\n", options=options)

    assert result.rows == (("1", "2", "3"),)
    assert result.warnings
    assert "row 2" in result.warnings[0].lower()
