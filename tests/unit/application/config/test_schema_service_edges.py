"""Edge-case coverage tests for config schema and service helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

import dpost.application.config.schema as schema_module
from dpost.application.config import (
    ActiveConfig,
    ConfigService,
    DeviceConfig,
    DeviceFileSelectors,
    DeviceLookupError,
    PCConfig,
    StabilityOverride,
    WatcherSettings,
)


def test_normalize_suffix_handles_empty_and_missing_dot() -> None:
    """Suffix normalization should preserve empty values and prepend dots."""

    assert schema_module._normalize_suffix("   ") == ""
    assert schema_module._normalize_suffix("csv") == ".csv"


def test_watcher_settings_coerces_single_override_and_mapping() -> None:
    """Watcher settings should accept override objects and mapping definitions."""

    single = StabilityOverride(suffixes=("csv",), stable_cycles=1)
    watcher_from_single = WatcherSettings(stability_overrides=single)
    assert watcher_from_single.stability_overrides == (single,)

    watcher_from_mapping = WatcherSettings(
        stability_overrides=(
            {
                "suffixes": (".txt",),
                "poll_seconds": 0.1,
            },
        )
    )
    assert len(watcher_from_mapping.stability_overrides) == 1
    assert watcher_from_mapping.stability_overrides[0].suffixes == (".txt",)


def test_watcher_settings_rejects_invalid_override_type() -> None:
    """Invalid override entries should fail with a clear type error."""

    with pytest.raises(TypeError):
        WatcherSettings(stability_overrides=(object(),))


def test_stability_override_matches_false_when_no_pattern_matches() -> None:
    """Overrides should return False when path misses both folder and suffix rules."""

    override = StabilityOverride(suffixes=(".csv",), folders=("batch",))
    assert override.matches(Path("sample.txt")) is False


def test_should_defer_dir_returns_false_for_non_directory(tmp_path: Path) -> None:
    """Non-directory paths should never be treated as deferred folders."""

    target = tmp_path / "sample.txt"
    target.write_text("payload")
    device = DeviceConfig(identifier="dev")

    assert device.should_defer_dir(target) is False


def test_should_defer_dir_returns_false_without_temp_regex(tmp_path: Path) -> None:
    """A missing temp-folder regex should disable defer-folder matching."""

    folder = tmp_path / "batch.abc123"
    folder.mkdir()
    device = DeviceConfig(identifier="dev")
    device.watcher.temp_folder_regex = None

    assert device.should_defer_dir(folder) is False


def test_should_defer_dir_uses_temp_regex_for_directory_names(tmp_path: Path) -> None:
    """Default temp regex should detect staging-style folder names."""

    temp_folder = tmp_path / "batch.abc123"
    temp_folder.mkdir()
    regular_folder = tmp_path / "batch"
    regular_folder.mkdir()
    device = DeviceConfig(identifier="dev")

    assert device.should_defer_dir(temp_folder) is True
    assert device.should_defer_dir(regular_folder) is False


def test_should_defer_dir_handles_path_name_access_errors(monkeypatch) -> None:
    """Path-name lookup failures should fail closed without raising."""

    class _BrokenPath:
        def __init__(self, *_args, **_kwargs):
            pass

        @staticmethod
        def is_dir() -> bool:
            return True

        @property
        def name(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(schema_module, "Path", _BrokenPath)
    device = DeviceConfig(identifier="dev")

    assert device.should_defer_dir("ignored") is False


def test_matches_file_rejects_temp_folder_names(tmp_path: Path) -> None:
    """Temp-style directory names should be excluded before content checks."""

    folder = tmp_path / "batch.abc123"
    folder.mkdir()
    (folder / "data.dat").write_text("payload")
    device = DeviceConfig(
        identifier="dev",
        files=DeviceFileSelectors(
            allowed_extensions=set(),
            allowed_folder_contents={".dat"},
        ),
    )

    assert device.matches_file(folder) is False


def test_matches_file_requires_allowed_folder_contents(tmp_path: Path) -> None:
    """Directory routing should fail when allowed folder contents are unset."""

    folder = tmp_path / "bundle"
    folder.mkdir()
    (folder / "data.dat").write_text("payload")
    device = DeviceConfig(
        identifier="dev",
        files=DeviceFileSelectors(
            allowed_extensions=set(),
            allowed_folder_contents=set(),
        ),
    )

    assert device.matches_file(folder) is False


def test_matches_file_handles_directory_rglob_disappearing(
    tmp_path: Path, monkeypatch
) -> None:
    """Racing directory disappearance during rglob should return False."""

    folder = tmp_path / "bundle"
    folder.mkdir()
    device = DeviceConfig(
        identifier="dev",
        files=DeviceFileSelectors(
            allowed_extensions=set(),
            allowed_folder_contents={".dat"},
        ),
    )

    def _raise_file_not_found(self: Path, pattern: str):
        raise FileNotFoundError

    monkeypatch.setattr(Path, "rglob", _raise_file_not_found)

    assert device.matches_file(folder) is False


def test_active_config_exposes_naming_and_none_metadata() -> None:
    """Active config should expose PC naming and None metadata when inactive."""

    active = ActiveConfig(pc=PCConfig(identifier="pc"), device=None)

    assert active.naming is active.pc.naming
    assert active.device_metadata is None


def test_active_config_exposes_filename_pattern() -> None:
    """Filename pattern should proxy through ActiveConfig naming settings."""

    active = ActiveConfig(pc=PCConfig(identifier="pc"), device=None)
    assert active.filename_pattern is active.pc.naming.filename_pattern


def test_register_device_requires_non_empty_identifier() -> None:
    """Device registration should fail for objects without identifier strings."""

    service = ConfigService(PCConfig(identifier="pc"))

    with pytest.raises(TypeError):
        service.register_device(object())


def test_get_device_raises_lookup_error_for_unknown_identifier() -> None:
    """Unknown device ids should raise DeviceLookupError."""

    service = ConfigService(PCConfig(identifier="pc"))

    with pytest.raises(DeviceLookupError):
        service.get_device("missing")


def test_matching_devices_ignores_deferred_device_candidates() -> None:
    """Deferred devices should be excluded from immediate matching results."""

    class _DeferredDevice:
        identifier = "deferred"

        @staticmethod
        def should_defer_dir(path_like):
            return True

        @staticmethod
        def matches_file(path_like):
            return True

    class _ReadyDevice:
        identifier = "ready"

        @staticmethod
        def should_defer_dir(path_like):
            return False

        @staticmethod
        def matches_file(path_like):
            return True

    service = ConfigService(PCConfig(identifier="pc"), [_DeferredDevice(), _ReadyDevice()])

    matches = service.matching_devices("sample.txt")

    assert [device.identifier for device in matches] == ["ready"]


def test_deferred_devices_returns_only_deferred_candidates() -> None:
    """Deferred-device listing should include only defer-eligible entries."""

    class _DeferredDevice:
        identifier = "deferred"

        @staticmethod
        def should_defer_dir(path_like):
            return True

        @staticmethod
        def matches_file(path_like):
            return False

    class _ReadyDevice:
        identifier = "ready"

        @staticmethod
        def should_defer_dir(path_like):
            return False

        @staticmethod
        def matches_file(path_like):
            return True

    service = ConfigService(PCConfig(identifier="pc"), [_DeferredDevice(), _ReadyDevice()])

    deferred = service.deferred_devices("sample.txt")

    assert [device.identifier for device in deferred] == ["deferred"]


def test_service_set_and_clear_active_device() -> None:
    """Manual active-device setters should update and clear context."""

    service = ConfigService(PCConfig(identifier="pc"))
    device = DeviceConfig(identifier="dev")

    service.set_active_device(device)
    assert service.current_device() is device

    service.clear_active_device()
    assert service.current_device() is None


def test_service_pc_and_current_properties_return_expected_objects() -> None:
    """Service property accessors should expose PC config and active wrapper."""

    pc = PCConfig(identifier="pc")
    service = ConfigService(pc)
    device = DeviceConfig(identifier="dev")
    service.set_active_device(device)

    assert service.pc is pc
    assert service.current.device is device


def test_defer_and_match_helpers_handle_errors_and_missing_callables() -> None:
    """Static helper guards should safely default to False on bad devices."""

    class _BrokenDefer:
        @staticmethod
        def should_defer_dir(path_like):
            raise RuntimeError("boom")

    class _NoDeferCallable:
        should_defer_dir = None

    class _BrokenMatch:
        @staticmethod
        def matches_file(path_like):
            raise RuntimeError("boom")

    class _NoMatchCallable:
        matches_file = None

    assert ConfigService._device_should_defer(_BrokenDefer(), "x") is False
    assert ConfigService._device_should_defer(_NoDeferCallable(), "x") is False
    assert ConfigService._device_matches_file(_BrokenMatch(), "x") is False
    assert ConfigService._device_matches_file(_NoMatchCallable(), "x") is False


def test_activation_context_handles_none_device() -> None:
    """Activating with None should explicitly set no active device."""

    service = ConfigService(PCConfig(identifier="pc"))

    with service.activate_device(None) as resolved:
        assert resolved is None
        assert service.current_device() is None


def test_activation_context_accepts_duck_typed_device() -> None:
    """Activation should accept external devices with required matcher hooks."""

    class _ExternalDevice:
        identifier = "external"

        @staticmethod
        def should_defer_dir(path_like):
            return False

        @staticmethod
        def matches_file(path_like):
            return True

    service = ConfigService(PCConfig(identifier="pc"))
    external = _ExternalDevice()

    with service.activate_device(external) as resolved:
        assert resolved is external
        assert service.current_device() is external


def test_activation_context_uses_registered_device_for_matching_identifier() -> None:
    """Passing an object with a known identifier should resolve to registered device."""

    service = ConfigService(PCConfig(identifier="pc"))
    registered = DeviceConfig(identifier="known")
    service.register_device(registered)

    class _IdentifierOnly:
        identifier = "known"

    with service.activate_device(_IdentifierOnly()) as resolved:
        assert resolved is registered


def test_activation_context_raises_for_unresolvable_device() -> None:
    """Activation should raise lookup errors for unrecognized device objects."""

    service = ConfigService(PCConfig(identifier="pc"))

    with pytest.raises(DeviceLookupError):
        with service.activate_device(object()):
            pass
