from __future__ import annotations

from pathlib import Path

import pytest

from dpost_v2.application.startup.settings import (
    SettingsRangeError,
    SettingsShapeError,
    from_raw,
    to_redacted_dict,
)


def _raw_payload() -> dict:
    return {
        "mode": "HEADLESS",
        "profile": "CI",
        "paths": {
            "root": "runtime",
            "watch": "incoming",
            "dest": "processed",
            "staging": "tmp",
        },
        "ui": {"backend": "headless"},
        "sync": {"backend": "noop", "api_token": "secret-token"},
        "ingestion": {"retry_limit": 2, "retry_delay_seconds": 0.5},
        "naming": {"prefix": "LAB", "policy": "prefix_only"},
    }


def test_from_raw_normalizes_mode_profile_and_paths(tmp_path: Path) -> None:
    settings = from_raw(_raw_payload(), root_hint=tmp_path)

    assert settings.mode == "headless"
    assert settings.profile == "ci"
    assert settings.paths.root == str((tmp_path / "runtime").resolve())
    assert settings.paths.watch == str((tmp_path / "runtime" / "incoming").resolve())
    assert settings.paths.dest == str((tmp_path / "runtime" / "processed").resolve())


def test_from_raw_rejects_negative_retry_values(tmp_path: Path) -> None:
    payload = _raw_payload()
    payload["ingestion"]["retry_limit"] = -1

    with pytest.raises(SettingsRangeError, match="retry_limit"):
        from_raw(payload, root_hint=tmp_path)


def test_from_raw_requires_nested_blocks(tmp_path: Path) -> None:
    payload = _raw_payload()
    payload.pop("naming")

    with pytest.raises(SettingsShapeError, match="naming"):
        from_raw(payload, root_hint=tmp_path)


def test_to_redacted_dict_masks_sync_secret(tmp_path: Path) -> None:
    settings = from_raw(_raw_payload(), root_hint=tmp_path)
    redacted = to_redacted_dict(settings)

    assert redacted["sync"]["backend"] == "noop"
    assert redacted["sync"]["api_token"] == "<redacted>"
