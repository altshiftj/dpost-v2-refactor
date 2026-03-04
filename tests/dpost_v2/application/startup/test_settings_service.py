from __future__ import annotations

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

    first = load_startup_settings(request, root_hint=tmp_path, sources=sources, cache=cache)
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
    assert SettingsCacheIntegrityError.__name__ in result.diagnostics["cache_integrity_error"]
