"""Unit coverage for pure naming identifier helper functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from dpost.domain.naming.identifiers import (
    generate_file_id,
    generate_record_id,
    parse_filename,
)


def test_parse_filename_returns_stem_and_suffix() -> None:
    """Split a path-like value into stem and extension components."""
    stem, suffix = parse_filename(str(Path("C:/input/run/sample.csv")))
    assert stem == "sample"
    assert suffix == ".csv"


def test_generate_record_id_lowercases_composed_identifier() -> None:
    """Compose canonical record ID and normalize full output to lowercase."""
    result = generate_record_id(
        "MuS-IPAT-Sample_A",
        dev_kadi_record_id="REC01",
        id_separator="-",
    )
    assert result == "rec01-mus-ipat-sample_a"


def test_generate_file_id_uses_sample_segments_after_prefix_fields() -> None:
    """Generate file ID from device abbreviation and sample segment(s)."""
    result = generate_file_id(
        "mus-ipat-sample-a01",
        device_abbr="RHE",
        id_separator="-",
    )
    assert result == "RHE-sample-a01"


def test_generate_file_id_raises_for_prefix_without_three_segments() -> None:
    """Reject prefixes that do not include user, institute, and sample segments."""
    with pytest.raises(ValueError, match="does not contain three segments"):
        generate_file_id(
            "mus-ipat",
            device_abbr="SEM",
            id_separator="-",
        )
