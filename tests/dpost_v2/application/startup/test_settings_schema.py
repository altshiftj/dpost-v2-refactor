from __future__ import annotations

import pytest

from dpost_v2.application.startup.settings_schema import (
    SettingsSchemaAliasError,
    SettingsSchemaConstraintError,
    SettingsSchemaMissingFieldError,
    SettingsSchemaValueError,
    validate_raw_settings,
)


def test_schema_normalizes_aliases_to_canonical_paths() -> None:
    validated = validate_raw_settings(
        {
            "runtime_mode": "HEADLESS",
            "runtime_profile": "ci",
            "paths": {"root": "./sandbox"},
            "ui_backend": "headless",
            "sync_backend": "noop",
            "naming": {"prefix": "LAB"},
            "ingestion": {"retry_limit": 3, "retry_delay_seconds": 0.25},
        }
    )

    assert validated["mode"] == "headless"
    assert validated["profile"] == "ci"
    assert validated["ui"]["backend"] == "headless"
    assert validated["sync"]["backend"] == "noop"


def test_schema_rejects_missing_required_fields_with_stable_code() -> None:
    with pytest.raises(SettingsSchemaMissingFieldError) as exc_info:
        validate_raw_settings({"profile": "ci"})

    assert exc_info.value.issues[0].code == "missing_field"
    assert exc_info.value.issues[0].path == "mode"


def test_schema_rejects_invalid_enum_with_stable_code() -> None:
    with pytest.raises(SettingsSchemaValueError) as exc_info:
        validate_raw_settings(
            {
                "mode": "invalid-mode",
                "profile": "ci",
                "paths": {"root": "./sandbox"},
            }
        )

    assert exc_info.value.issues[0].code == "invalid_enum"
    assert exc_info.value.issues[0].path == "mode"


def test_schema_rejects_cross_field_mode_ui_contradiction() -> None:
    with pytest.raises(SettingsSchemaConstraintError) as exc_info:
        validate_raw_settings(
            {
                "mode": "desktop",
                "profile": "ci",
                "paths": {"root": "./sandbox"},
                "ui": {"backend": "headless"},
            }
        )

    assert exc_info.value.issues[0].code == "constraint_violation"
    assert exc_info.value.issues[0].path == "ui.backend"


def test_schema_rejects_alias_collision() -> None:
    with pytest.raises(SettingsSchemaAliasError) as exc_info:
        validate_raw_settings(
            {
                "mode": "headless",
                "runtime_mode": "desktop",
                "profile": "ci",
                "paths": {"root": "./sandbox"},
            }
        )

    assert exc_info.value.issues[0].code == "alias_collision"
    assert exc_info.value.issues[0].path == "runtime_mode"
