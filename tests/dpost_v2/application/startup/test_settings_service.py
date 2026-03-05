from __future__ import annotations

import json
from pathlib import Path

from dpost_v2.application.startup.bootstrap import BootstrapRequest
from dpost_v2.application.startup.settings_service import (
    SettingsCache,
    SettingsCacheEntry,
    SettingsCacheIntegrityError,
    load_startup_settings,
)


def _request() -> BootstrapRequest:
    return BootstrapRequest(mode="headless", profile="ci", trace_id="trace-settings")


def test_settings_service_applies_source_precedence_and_provenance(
    tmp_path: Path,
) -> None:
    request = _request()
    result = load_startup_settings(
        request,
        root_hint=tmp_path,
        sources={
            "defaults": {
                "mode": "headless",
                "profile": "default",
                "paths": {"root": "defaults"},
                "ui": {"backend": "headless"},
                "sync": {"backend": "noop"},
                "ingestion": {"retry_limit": 1, "retry_delay_seconds": 1.0},
                "naming": {"prefix": "DEF", "policy": "prefix_only"},
            },
            "file": {"profile": "file", "naming": {"prefix": "FILE"}},
            "environment": {"profile": "env"},
            "cli": {"profile": "cli", "naming": {"prefix": "CLI"}},
        },
    )

    assert result.is_success is True
    assert result.settings is not None
    assert result.settings.profile == "cli"
    assert result.settings.naming.prefix == "CLI"
    assert result.provenance["profile"] == "cli"
    assert result.provenance["naming.prefix"] == "cli"


def test_settings_service_reads_plugin_policy_from_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PC_NAME", "legacy_pc")
    monkeypatch.setenv("DPOST_PC_NAME", "tischrem_blb")
    monkeypatch.setenv("DEVICE_PLUGINS", "legacy_device")
    monkeypatch.setenv("DPOST_DEVICE_PLUGINS", "sem_phenomxl2; utm_zwick")

    request = BootstrapRequest(
        mode="v2",
        profile="prod",
        trace_id="trace-settings-env-plugins",
        metadata={},
    )
    result = load_startup_settings(request, root_hint=tmp_path)

    assert result.is_success is True
    assert result.settings is not None
    assert result.settings.plugins.pc_name == "tischrem_blb"
    assert result.settings.plugins.device_plugins == (
        "sem_phenomxl2",
        "utm_zwick",
    )
    assert result.provenance["plugins.pc_name"] == "environment"
    assert result.provenance["plugins.device_plugins"] == "environment"


def test_settings_service_reuses_cache_for_unchanged_fingerprint(
    tmp_path: Path,
) -> None:
    request = _request()
    cache = SettingsCache()
    sources = {
        "defaults": {
            "mode": "headless",
            "profile": "default",
            "paths": {"root": "defaults"},
            "ui": {"backend": "headless"},
            "sync": {"backend": "noop"},
            "ingestion": {"retry_limit": 1, "retry_delay_seconds": 1.0},
            "naming": {"prefix": "DEF", "policy": "prefix_only"},
        },
        "file": {},
        "environment": {},
        "cli": {},
    }

    first = load_startup_settings(
        request, root_hint=tmp_path, sources=sources, cache=cache
    )
    second = load_startup_settings(
        request,
        root_hint=tmp_path,
        sources=sources,
        cache=cache,
    )

    assert first.is_success is True
    assert second.is_success is True
    assert second.diagnostics["cache_hit"] is True
    assert first.settings is second.settings


def test_settings_service_maps_v2_request_mode_to_headless_runtime_mode(
    tmp_path: Path,
) -> None:
    request = BootstrapRequest(
        mode="v2",
        profile="ci",
        trace_id="trace-settings-v2",
        metadata={"headless": True},
    )
    result = load_startup_settings(
        request,
        root_hint=tmp_path,
        sources={
            "defaults": {
                "mode": "headless",
                "profile": "default",
                "paths": {"root": "defaults"},
                "ui": {"backend": "headless"},
                "sync": {"backend": "noop"},
                "ingestion": {"retry_limit": 1, "retry_delay_seconds": 1.0},
                "naming": {"prefix": "DEF", "policy": "prefix_only"},
            },
            "file": {},
            "environment": {},
            "cli": {"profile": "ci"},
        },
    )

    assert result.is_success is True
    assert result.settings is not None
    assert result.settings.mode == "headless"


def test_settings_service_loads_config_file_source(tmp_path: Path) -> None:
    config_file = tmp_path / "dpost-v2.config.json"
    config_file.write_text(
        json.dumps(
            {
                "mode": "headless",
                "profile": "prod",
                "paths": {
                    "root": ".",
                    "watch": "incoming",
                    "dest": "processed",
                    "staging": "tmp",
                },
                "ui": {"backend": "headless"},
                "sync": {"backend": "noop"},
                "ingestion": {"retry_limit": 2, "retry_delay_seconds": 1.5},
                "naming": {"prefix": "CONFIG", "policy": "prefix_only"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    request = BootstrapRequest(
        mode="v2",
        profile=None,
        trace_id="trace-settings-config",
        metadata={"config_path": str(config_file)},
    )
    result = load_startup_settings(request, root_hint=tmp_path)

    assert result.is_success is True
    assert result.settings is not None
    assert result.settings.profile == "prod"
    assert result.settings.naming.prefix == "CONFIG"
    assert result.settings.mode == "headless"


def test_settings_service_cli_profile_takes_precedence_over_config(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "dpost-v2.config.json"
    config_file.write_text(
        json.dumps(
            {
                "mode": "headless",
                "profile": "prod",
                "paths": {
                    "root": ".",
                    "watch": "incoming",
                    "dest": "processed",
                    "staging": "tmp",
                },
                "ui": {"backend": "headless"},
                "sync": {"backend": "noop"},
                "ingestion": {"retry_limit": 2, "retry_delay_seconds": 1.5},
                "naming": {"prefix": "CONFIG", "policy": "prefix_only"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    request = BootstrapRequest(
        mode="v2",
        profile="ci",
        trace_id="trace-settings-config-cli",
        metadata={"config_path": str(config_file)},
    )
    result = load_startup_settings(request, root_hint=tmp_path)

    assert result.is_success is True
    assert result.settings is not None
    assert result.settings.profile == "ci"


def test_settings_service_fails_on_missing_config_path(tmp_path: Path) -> None:
    request = BootstrapRequest(
        mode="v2",
        profile="ci",
        trace_id="trace-settings-config-missing",
        metadata={"config_path": str(tmp_path / "missing.json")},
    )
    result = load_startup_settings(request, root_hint=tmp_path)

    assert result.is_success is False
    assert result.failure is not None
    assert result.failure.stage == "settings_service"
    assert "Config file not found" in result.failure.message


def test_settings_service_detects_cache_desync_and_recovers(tmp_path: Path) -> None:
    request = _request()
    cache = SettingsCache(
        entry=SettingsCacheEntry(
            fingerprint="fingerprint-a",
            settings=None,
            diagnostics={},
            settings_fingerprint="fingerprint-b",
        )
    )

    result = load_startup_settings(
        request,
        root_hint=tmp_path,
        sources={
            "defaults": {
                "mode": "headless",
                "profile": "default",
                "paths": {"root": "defaults"},
                "ui": {"backend": "headless"},
                "sync": {"backend": "noop"},
                "ingestion": {"retry_limit": 1, "retry_delay_seconds": 1.0},
                "naming": {"prefix": "DEF", "policy": "prefix_only"},
            },
            "file": {},
            "environment": {},
            "cli": {},
        },
        cache=cache,
    )

    assert result.is_success is True
    assert "cache_integrity_error" in result.diagnostics
    assert (
        SettingsCacheIntegrityError.__name__
        in result.diagnostics["cache_integrity_error"]
    )
