"""Unit coverage for application naming facade delegation and context use."""

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


@dataclass(frozen=True)
class _Config:
    """Synthetic active naming config used for policy facade tests."""

    id_separator: str
    filename_pattern: re.Pattern[str]
    device: _Device | None


def _install_current(monkeypatch: pytest.MonkeyPatch, config: _Config) -> None:
    """Patch active config accessor to return the supplied config object."""
    monkeypatch.setattr(policy, "current", lambda: config)


def test_generate_record_id_uses_explicit_record_id_without_device_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate record ID directly from explicit record ID argument."""
    _install_current(
        monkeypatch,
        _Config(id_separator="-", filename_pattern=FILENAME_PATTERN, device=None),
    )

    record_id = policy.generate_record_id(
        "mus-ipat-sample_1",
        dev_kadi_record_id="REC01",
    )

    assert record_id == "rec01-mus-ipat-sample_1"


def test_generate_record_id_uses_active_device_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate record ID from active device metadata when explicit ID is absent."""
    _install_current(
        monkeypatch,
        _Config(
            id_separator="-",
            filename_pattern=FILENAME_PATTERN,
            device=_Device(_Metadata(device_abbr="SEM", record_kadi_id="RID99")),
        ),
    )

    record_id = policy.generate_record_id("mus-ipat-sample_1")

    assert record_id == "rid99-mus-ipat-sample_1"


def test_generate_record_id_raises_without_active_record_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise when neither explicit ID nor active device record ID is available."""
    _install_current(
        monkeypatch,
        _Config(id_separator="-", filename_pattern=FILENAME_PATTERN, device=None),
    )

    with pytest.raises(ValueError, match="Device context is not set"):
        policy.generate_record_id("mus-ipat-sample_1")


def test_generate_file_id_uses_active_device_abbreviation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate file ID from active device metadata when abbreviation is omitted."""
    _install_current(
        monkeypatch,
        _Config(
            id_separator="-",
            filename_pattern=FILENAME_PATTERN,
            device=_Device(_Metadata(device_abbr="RHE", record_kadi_id="RID1")),
        ),
    )

    file_id = policy.generate_file_id("mus-ipat-sample_1")

    assert file_id == "RHE-sample_1"


def test_generate_file_id_raises_without_active_device_abbreviation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise when neither explicit abbreviation nor active device context exists."""
    _install_current(
        monkeypatch,
        _Config(id_separator="-", filename_pattern=FILENAME_PATTERN, device=None),
    )

    with pytest.raises(ValueError, match="Device context is not set"):
        policy.generate_file_id("mus-ipat-sample_1")


def test_parse_and_prefix_wrapper_helpers_use_active_policy_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delegate parse/validate/sanitize helpers through active naming settings."""
    _install_current(
        monkeypatch,
        _Config(id_separator="-", filename_pattern=FILENAME_PATTERN, device=None),
    )

    stem, suffix = policy.parse_filename("C:/tmp/demo.txt")
    assert (stem, suffix) == ("demo", ".txt")

    assert policy.is_valid_prefix("mus-ipat-sample_1") is True
    assert policy.sanitize_prefix(" MuS - IPAT - Sample Name ") == "mus-ipat-Sample_Name"
    sanitized, valid = policy.sanitize_and_validate("MuS-IPAT-Sample Name")
    assert sanitized == "mus-ipat-Sample_Name"
    assert valid is True


def test_violation_and_user_input_analysis_wrappers_delegate_to_domain_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return domain-analysis outputs using active filename pattern and separator."""
    _install_current(
        monkeypatch,
        _Config(id_separator="-", filename_pattern=FILENAME_PATTERN, device=None),
    )

    violation = policy.explain_filename_violation("u1-ipat-sample!")
    assert violation["valid"] is False
    assert violation["reasons"]

    analysis = policy.analyze_user_input(
        {"name": "MuS", "institute": "IPAT", "sample_ID": "Sample Name"}
    )
    assert analysis["valid"] is True
    assert analysis["sanitized"] == "mus-ipat-Sample_Name"
