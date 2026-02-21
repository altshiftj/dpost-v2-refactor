"""Unit coverage for pure prefix sanitization and validation policy rules."""

from __future__ import annotations

import re

from dpost.domain.naming.prefix_policy import (
    ValidationMessages,
    analyze_user_input,
    explain_filename_violation,
    is_valid_prefix,
    sanitize_and_validate,
    sanitize_prefix,
)

FILENAME_PATTERN = re.compile(r"^[A-Za-z]+-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}$")


def test_is_valid_prefix_requires_pattern_match_and_three_segments() -> None:
    """Validate only prefixes that match regex and include separator structure."""
    assert is_valid_prefix(
        "mus-ipat-Sample_1",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert not is_valid_prefix(
        "mus-ipat",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert not is_valid_prefix(
        "mu5-ipat-Sample",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )


def test_sanitize_prefix_normalizes_user_institute_and_sample_spaces() -> None:
    """Lowercase first two fields and replace spaces in sample segment(s)."""
    sanitized = sanitize_prefix(" MuS - IPAT - Sample Name 01 ", id_separator="-")
    assert sanitized == "mus-ipat-Sample_Name_01"


def test_sanitize_prefix_returns_input_when_segments_are_incomplete() -> None:
    """Keep value unchanged when prefix does not contain all required segments."""
    raw = "mus-ipat"
    assert sanitize_prefix(raw, id_separator="-") == raw


def test_sanitize_and_validate_returns_raw_when_invalid() -> None:
    """Return original value and invalid flag when prefix does not satisfy policy."""
    sanitized, valid = sanitize_and_validate(
        "mus-ipat",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert sanitized == "mus-ipat"
    assert valid is False


def test_sanitize_and_validate_returns_sanitized_value_when_valid() -> None:
    """Return sanitized prefix plus valid flag for policy-compliant input."""
    sanitized, valid = sanitize_and_validate(
        "MuS-IPAT-Sample A",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert sanitized == "mus-ipat-Sample_A"
    assert valid is True


def test_explain_filename_violation_returns_valid_for_matching_prefix() -> None:
    """Return empty reasons/highlights when filename already satisfies policy."""
    analysis = explain_filename_violation(
        "mus-ipat-Sample_1",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is True
    assert analysis["reasons"] == []
    assert analysis["highlight_spans"] == []


def test_explain_filename_violation_reports_separator_issues() -> None:
    """Flag separator layout errors and highlight separator character positions."""
    analysis = explain_filename_violation(
        "a-b-c-d",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is False
    assert ValidationMessages.MISSING_SEPARATOR in analysis["reasons"]
    assert analysis["highlight_spans"] == [(1, 2), (3, 4), (5, 6)]


def test_explain_filename_violation_reports_segment_character_issues() -> None:
    """Highlight invalid user/institute/sample characters for rename guidance."""
    analysis = explain_filename_violation(
        "u1-i2-sample!",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is False
    assert ValidationMessages.USER_ONLY_LETTERS in analysis["reasons"]
    assert ValidationMessages.INSTITUTE_ONLY_LETTERS in analysis["reasons"]
    assert ValidationMessages.SAMPLE_INVALID_CHARS in analysis["reasons"]
    assert (1, 2) in analysis["highlight_spans"]
    assert (4, 5) in analysis["highlight_spans"]
    assert (12, 13) in analysis["highlight_spans"]


def test_explain_filename_violation_reports_sample_length_limit() -> None:
    """Add sample-length reason when sample segment exceeds policy limit."""
    analysis = explain_filename_violation(
        f"mus-ipat-{'x' * 31}",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is False
    assert ValidationMessages.SAMPLE_TOO_LONG in analysis["reasons"]


def test_analyze_user_input_returns_cancel_reason_when_dialog_cancelled() -> None:
    """Return invalid analysis with explicit cancel reason when user aborts dialog."""
    analysis = analyze_user_input(
        None,
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is False
    assert analysis["sanitized"] is None
    assert analysis["reasons"] == ["User cancelled the dialog."]


def test_analyze_user_input_returns_sanitized_value_for_valid_fields() -> None:
    """Return sanitized prefix for valid rename values."""
    analysis = analyze_user_input(
        {"name": "MuS", "institute": "IPAT", "sample_ID": "Sample A"},
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is True
    assert analysis["sanitized"] == "mus-ipat-Sample_A"
    assert analysis["reasons"] == []
    assert analysis["highlight_spans"] == []


def test_analyze_user_input_reports_reasons_for_invalid_fields() -> None:
    """Aggregate validation reasons/highlights when rename values are invalid."""
    analysis = analyze_user_input(
        {"name": "u1", "institute": "i2", "sample_ID": "sample!"},
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is False
    assert analysis["sanitized"] is None
    assert ValidationMessages.USER_ONLY_LETTERS in analysis["reasons"]
    assert ValidationMessages.INSTITUTE_ONLY_LETTERS in analysis["reasons"]
    assert ValidationMessages.SAMPLE_INVALID_CHARS in analysis["reasons"]
    assert analysis["highlight_spans"]
