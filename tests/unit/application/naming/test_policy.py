"""Unit coverage for explicit-context naming facade behavior."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest

import dpost.application.naming.policy as policy

FILENAME_PATTERN = re.compile(r"^[A-Za-z]+-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}$")


@dataclass(frozen=True)
class _Metadata:
    """Synthetic device metadata for naming context resolution tests."""

    device_abbr: str | None
    record_kadi_id: str | None


@dataclass(frozen=True)
class _Device:
    """Synthetic active device wrapper with metadata payload."""

    metadata: _Metadata


def test_generate_record_id_uses_explicit_record_id_and_separator() -> None:
    """Generate record IDs without any ambient naming config dependency."""
    record_id = policy.generate_record_id(
        "mus-ipat-sample_1",
        dev_kadi_record_id="REC01",
        id_separator="-",
    )

    assert record_id == "rec01-mus-ipat-sample_1"


def test_generate_record_id_uses_explicit_device_context() -> None:
    """Generate record ID from provided device metadata when record id is omitted."""
    device = _Device(_Metadata(device_abbr="SEM", record_kadi_id="RID99"))
    record_id = policy.generate_record_id(
        "mus-ipat-sample_1",
        id_separator="-",
        current_device=device,
    )

    assert record_id == "rid99-mus-ipat-sample_1"


def test_generate_record_id_requires_separator() -> None:
    """Reject record ID generation when separator context is not supplied."""
    with pytest.raises(TypeError, match="required keyword-only argument: 'id_separator'"):
        policy.generate_record_id(
            "mus-ipat-sample_1",
            dev_kadi_record_id="REC01",
        )


def test_generate_record_id_requires_device_or_explicit_record_id() -> None:
    """Reject record ID generation when record context is missing."""
    with pytest.raises(ValueError, match="Device context is not set"):
        policy.generate_record_id("mus-ipat-sample_1", id_separator="-")


def test_generate_file_id_uses_explicit_context() -> None:
    """Generate file ID from provided device context and explicit separator."""
    device = _Device(_Metadata(device_abbr="RHE", record_kadi_id="RID1"))
    file_id = policy.generate_file_id(
        "mus-ipat-sample_1",
        id_separator="-",
        current_device=device,
    )

    assert file_id == "RHE-sample_1"


def test_generate_file_id_requires_separator() -> None:
    """Reject file ID generation when separator context is missing."""
    with pytest.raises(TypeError, match="required keyword-only argument: 'id_separator'"):
        policy.generate_file_id("mus-ipat-sample_1", device_abbr="RHE")


def test_generate_file_id_requires_device_or_explicit_abbr() -> None:
    """Reject file ID generation when device context is missing."""
    with pytest.raises(ValueError, match="Device context is not set"):
        policy.generate_file_id("mus-ipat-sample_1", id_separator="-")


def test_parse_and_prefix_helpers_require_explicit_context() -> None:
    """Parse should stay context-free while prefix helpers demand explicit policy."""
    stem, suffix = policy.parse_filename("C:/tmp/demo.txt")
    assert (stem, suffix) == ("demo", ".txt")

    with pytest.raises(
        TypeError,
        match="required keyword-only argument: 'filename_pattern'",
    ):
        policy.is_valid_prefix("mus-ipat-sample_1", id_separator="-")
    with pytest.raises(TypeError, match="required keyword-only argument: 'id_separator'"):
        policy.sanitize_prefix(" MuS - IPAT - Sample Name ")

    assert (
        policy.sanitize_prefix(" MuS - IPAT - Sample Name ", id_separator="-")
        == "mus-ipat-Sample_Name"
    )
    sanitized, valid = policy.sanitize_and_validate(
        "MuS-IPAT-Sample Name",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert sanitized == "mus-ipat-Sample_Name"
    assert valid is True


def test_analysis_helpers_require_explicit_context() -> None:
    """Violation and rename-input analysis should reject missing naming policy."""
    with pytest.raises(
        TypeError,
        match="required keyword-only argument: 'filename_pattern'",
    ):
        policy.explain_filename_violation("u1-ipat-sample!", id_separator="-")
    with pytest.raises(TypeError, match="required keyword-only argument: 'id_separator'"):
        policy.analyze_user_input(
            {"name": "MuS", "institute": "IPAT", "sample_ID": "Sample Name"},
            filename_pattern=FILENAME_PATTERN,
        )

    violation = policy.explain_filename_violation(
        "u1-ipat-sample!",
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert violation["valid"] is False
    assert violation["reasons"]

    analysis = policy.analyze_user_input(
        {"name": "MuS", "institute": "IPAT", "sample_ID": "Sample Name"},
        filename_pattern=FILENAME_PATTERN,
        id_separator="-",
    )
    assert analysis["valid"] is True
    assert analysis["sanitized"] == "mus-ipat-Sample_Name"


def test_prefix_helpers_reject_empty_separator_value() -> None:
    """Reject explicit empty separator values even with strict function signatures."""
    with pytest.raises(ValueError, match="id_separator must be provided"):
        policy.sanitize_prefix("mus-ipat-sample_1", id_separator="")


def test_prefix_helpers_reject_explicit_none_pattern_value() -> None:
    """Reject explicit None patterns passed at runtime despite strict signatures."""
    with pytest.raises(ValueError, match="filename_pattern must be provided"):
        policy.is_valid_prefix(
            "mus-ipat-sample_1",
            filename_pattern=None,  # type: ignore[arg-type]
            id_separator="-",
        )
