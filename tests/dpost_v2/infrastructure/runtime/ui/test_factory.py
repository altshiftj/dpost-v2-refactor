from __future__ import annotations

import pytest

from dpost_v2.infrastructure.runtime.ui.factory import (
    UiFactoryBackendUnavailableError,
    UiFactoryContractError,
    UiFactoryInitializationError,
    UiFactoryModeError,
    build_ui_adapter,
)


def test_factory_selects_headless_mode_by_default() -> None:
    selection = build_ui_adapter(mode="headless")

    assert selection.descriptor["mode"] == "headless"
    assert selection.descriptor["backend"] == "headless"


def test_factory_rejects_unknown_mode() -> None:
    with pytest.raises(UiFactoryModeError):
        build_ui_adapter(mode="vr")


def test_factory_fails_desktop_mode_when_capabilities_are_missing() -> None:
    with pytest.raises(UiFactoryBackendUnavailableError):
        build_ui_adapter(
            mode="desktop",
            probes={
                "display_available": lambda: False,
                "tkinter_available": lambda: True,
            },
        )


def test_factory_maps_adapter_contract_mismatch() -> None:
    class _BrokenAdapter:
        def initialize(self) -> None:
            return None

    with pytest.raises(UiFactoryContractError):
        build_ui_adapter(
            mode="headless",
            constructors={"headless": lambda: _BrokenAdapter()},
        )


def test_factory_maps_initialization_failures() -> None:
    class _BadInit:
        def initialize(self) -> None:
            raise RuntimeError("boom")

        def notify(self, *, severity: str, title: str, message: str) -> None:
            return None

        def prompt(
            self, *, prompt_type: str, payload: dict[str, object]
        ) -> dict[str, object]:
            return {}

        def show_status(self, *, message: str) -> None:
            return None

        def shutdown(self) -> None:
            return None

    with pytest.raises(UiFactoryInitializationError):
        build_ui_adapter(
            mode="headless",
            constructors={"headless": lambda: _BadInit()},
        )
