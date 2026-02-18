"""Migration tests for Phase 4 naming/constants consolidation behavior."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from ipat_watchdog.core.config import init_config, reset_service
from ipat_watchdog.device_plugins.test_device.settings import (
    build_config as build_device_config,
)
from ipat_watchdog.pc_plugins.test_pc.settings import build_config as build_pc_config


def _missing_config_service() -> None:
    """Raise the canonical runtime error for missing config service."""
    raise RuntimeError("Configuration service has not been initialised")


def _reload_sync_kadi_module_with_stubbed_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    """Reload `sync_kadi` with lightweight `kadi_apy` stubs for migration tests."""
    kadi_module = ModuleType("kadi_apy")
    kadi_module.KadiManager = type("KadiManager", (), {})

    lib_module = ModuleType("kadi_apy.lib")
    resources_module = ModuleType("kadi_apy.lib.resources")

    records_module = ModuleType("kadi_apy.lib.resources.records")
    records_module.Record = type("Record", (), {})

    groups_module = ModuleType("kadi_apy.lib.resources.groups")
    groups_module.Group = type("Group", (), {})

    users_module = ModuleType("kadi_apy.lib.resources.users")
    users_module.User = type("User", (), {})

    collections_module = ModuleType("kadi_apy.lib.resources.collections")
    collections_module.Collection = type("Collection", (), {})

    monkeypatch.setitem(sys.modules, "kadi_apy", kadi_module)
    monkeypatch.setitem(sys.modules, "kadi_apy.lib", lib_module)
    monkeypatch.setitem(sys.modules, "kadi_apy.lib.resources", resources_module)
    monkeypatch.setitem(sys.modules, "kadi_apy.lib.resources.records", records_module)
    monkeypatch.setitem(sys.modules, "kadi_apy.lib.resources.groups", groups_module)
    monkeypatch.setitem(sys.modules, "kadi_apy.lib.resources.users", users_module)
    monkeypatch.setitem(
        sys.modules,
        "kadi_apy.lib.resources.collections",
        collections_module,
    )

    sys.modules.pop("ipat_watchdog.core.sync.sync_kadi", None)
    return importlib.import_module("ipat_watchdog.core.sync.sync_kadi")


@pytest.fixture
def custom_separator_config(tmp_path: Path):
    """Initialize config service with a non-default naming separator for tests."""
    root = tmp_path / "sandbox"
    overrides = {
        "app_dir": root / "App",
        "watch_dir": root / "Upload",
        "dest_dir": root / "Data",
        "rename_dir": root / "Data" / "00_To_Rename",
        "exceptions_dir": root / "Data" / "01_Exceptions",
        "daily_records_json": root / "records.json",
    }

    pc_config = build_pc_config(override_paths=overrides)
    pc_config.naming.id_separator = ":"
    device_config = build_device_config()
    init_config(pc_config, [device_config])
    yield
    reset_service()


def test_local_record_parses_identifier_using_active_config_separator(
    custom_separator_config,
) -> None:
    """Parse LocalRecord identifier using active config naming separator."""
    from ipat_watchdog.core.records.local_record import LocalRecord

    record = LocalRecord(identifier="dev:usr:inst:sample_1")

    assert record.user == "usr"
    assert record.institute == "inst"
    assert record.sample_name == "sample_1"


def test_local_record_requires_active_config_for_separator_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail fast when LocalRecord separator is resolved without active config."""
    local_record_module = importlib.import_module(
        "ipat_watchdog.core.records.local_record"
    )
    monkeypatch.setattr(local_record_module, "current", _missing_config_service)

    with pytest.raises(
        RuntimeError, match="Configuration service has not been initialised"
    ):
        local_record_module.LocalRecord(identifier="dev-usr-inst-sample")


def test_sync_kadi_uses_active_config_separator_for_user_lookup(
    custom_separator_config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build Kadi user lookup identifiers from active config naming separator."""
    sync_kadi = _reload_sync_kadi_module_with_stubbed_dependencies(monkeypatch)
    sync_manager = sync_kadi.KadiSyncManager.__new__(sync_kadi.KadiSyncManager)
    sync_manager.interactions = SimpleNamespace(
        show_error=lambda *_args, **_kwargs: None
    )
    calls: dict[str, str] = {}

    class DummyDbManager:
        """Capture calls for user lookup assertions."""

        def user(self, *, username: str, identity_type: str):
            calls["username"] = username
            calls["identity_type"] = identity_type
            return object()

    local_record = SimpleNamespace(user="usr", institute="inst")

    result = sync_manager._get_db_user_from_local_record(DummyDbManager(), local_record)

    assert result is not None
    assert calls["identity_type"] == "local"
    assert calls["username"] == "usr:inst"


def test_sync_kadi_requires_active_config_for_separator_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail fast when sync naming separator is resolved without active config."""
    sync_kadi = _reload_sync_kadi_module_with_stubbed_dependencies(monkeypatch)
    sync_manager = sync_kadi.KadiSyncManager.__new__(sync_kadi.KadiSyncManager)
    sync_manager.interactions = SimpleNamespace(
        show_error=lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(sync_kadi, "current", _missing_config_service)

    class DummyDbManager:
        """Capture user lookup calls for failure-path verification."""

        def user(self, *, username: str, identity_type: str):
            return object()

    with pytest.raises(
        RuntimeError, match="Configuration service has not been initialised"
    ):
        sync_manager._get_db_user_from_local_record(
            DummyDbManager(),
            SimpleNamespace(user="usr", institute="inst"),
        )


def test_psa_separator_requires_active_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject PSA separator fallback when config service is unavailable."""
    module = importlib.import_module(
        "ipat_watchdog.device_plugins.psa_horiba.file_processor"
    )
    monkeypatch.setattr(module, "current", _missing_config_service)

    with pytest.raises(
        RuntimeError, match="Configuration service has not been initialised"
    ):
        module._id_separator()


def test_rhe_separator_requires_active_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject Kinexus separator fallback when config service is unavailable."""
    module = importlib.import_module(
        "ipat_watchdog.device_plugins.rhe_kinexus.file_processor"
    )
    monkeypatch.setattr(module, "current", _missing_config_service)

    with pytest.raises(
        RuntimeError, match="Configuration service has not been initialised"
    ):
        module._id_separator()
