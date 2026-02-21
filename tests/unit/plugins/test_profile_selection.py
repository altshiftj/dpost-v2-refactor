"""Unit coverage for plugin profile selection boundary helpers."""

from __future__ import annotations

import pytest

from dpost.plugins.profile_selection import resolve_plugin_profile_selection
from dpost.plugins.reference import REFERENCE_PLUGIN_PROFILE


class ProfileSelectionError(RuntimeError):
    """Local startup error type used to verify raised message flow."""


def test_profile_selection_returns_none_when_no_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return ``None`` when no explicit, injected, or env profile is provided."""
    monkeypatch.delenv("DPOST_PLUGIN_PROFILE", raising=False)

    selected = resolve_plugin_profile_selection(
        startup_error_factory=ProfileSelectionError,
    )

    assert selected is None


def test_profile_selection_prefers_explicit_name_over_other_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use explicit profile input before env/injected profile values."""
    monkeypatch.setenv("DPOST_PLUGIN_PROFILE", "invalid")

    selected = resolve_plugin_profile_selection(
        profile_name=" reference ",
        env_profile_name="also-invalid",
        startup_error_factory=ProfileSelectionError,
    )

    assert selected is REFERENCE_PLUGIN_PROFILE


def test_profile_selection_uses_env_parameter_when_explicit_missing() -> None:
    """Use injected environment profile value when explicit input is absent."""
    selected = resolve_plugin_profile_selection(
        env_profile_name=" ReFeReNcE ",
        startup_error_factory=ProfileSelectionError,
    )

    assert selected is REFERENCE_PLUGIN_PROFILE


def test_profile_selection_reads_process_env_when_no_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback to process env lookup when no explicit values are passed."""
    monkeypatch.setenv("DPOST_PLUGIN_PROFILE", "reference")

    selected = resolve_plugin_profile_selection(
        startup_error_factory=ProfileSelectionError,
    )

    assert selected is REFERENCE_PLUGIN_PROFILE


def test_profile_selection_raises_for_unknown_profile_name() -> None:
    """Raise startup errors with available-profile guidance for invalid values."""
    with pytest.raises(ProfileSelectionError, match="Unknown plugin profile 'ghost'"):
        resolve_plugin_profile_selection(
            profile_name=" ghost ",
            startup_error_factory=ProfileSelectionError,
        )
