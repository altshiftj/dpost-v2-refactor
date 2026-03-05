from __future__ import annotations

from typing import Any

import pytest

import dpost.__main__ as dpost_entrypoint
import dpost_v2.__main__ as entrypoint
from dpost_v2.application.startup.bootstrap import BootstrapResult, StartupFailure


def test_main_defaults_mode_to_v2_and_calls_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        captured["request"] = request
        emit_event(type("Event", (), {"name": "startup_started", "payload": {}})())
        return BootstrapResult(is_success=True)

    monkeypatch.delenv("DPOST_MODE", raising=False)
    monkeypatch.delenv("DPOST_PROFILE", raising=False)
    monkeypatch.delenv("DPOST_CONFIG", raising=False)
    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main([])

    assert exit_code == 0
    assert captured["request"].mode == "v2"
    assert captured["request"].profile is None


def test_main_parses_explicit_args_into_bootstrap_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        captured["request"] = request
        emit_event(type("Event", (), {"name": "startup_started", "payload": {}})())
        return BootstrapResult(is_success=True)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(
        [
            "--mode",
            "v2",
            "--profile",
            "qa",
            "--config",
            "D:/configs/sample.yaml",
            "--headless",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    request = captured["request"]
    assert request.mode == "v2"
    assert request.profile == "qa"
    assert request.metadata["config_path"] == "D:/configs/sample.yaml"
    assert request.metadata["headless"] is True
    assert request.metadata["dry_run"] is True


@pytest.mark.parametrize("legacy_mode", ["v1", "shadow"])
def test_main_rejects_retired_cli_modes_before_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    legacy_mode: str,
) -> None:
    called = {"run": False}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        called["run"] = True
        return BootstrapResult(is_success=True)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", legacy_mode])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert called["run"] is False
    assert "usage: dpost " in captured.err
    assert f"invalid choice: '{legacy_mode}'" in captured.err


@pytest.mark.parametrize("legacy_mode", ["v1", "shadow"])
def test_main_rejects_retired_env_modes_before_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    legacy_mode: str,
) -> None:
    called = {"run": False}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        called["run"] = True
        return BootstrapResult(is_success=True)

    monkeypatch.setenv("DPOST_MODE", legacy_mode)
    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main([])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert called["run"] is False
    assert captured.err.strip() == f"Unsupported runtime mode: {legacy_mode}"


def test_main_rejects_invalid_cli_mode_before_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"run": False}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        called["run"] = True
        return BootstrapResult(is_success=True)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "broken"])

    assert exit_code == 2
    assert called["run"] is False


def test_main_success_message_uses_dpost_command_name(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True)

    monkeypatch.delenv("DPOST_MODE", raising=False)
    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "dpost startup succeeded" in captured.out
    assert "dpost_v2" not in captured.out


def test_main_maps_bootstrap_failure_to_exit_code_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        emit_event(type("Event", (), {"name": "startup_started", "payload": {}})())
        _ = request
        return BootstrapResult(
            is_success=False,
            failure=StartupFailure(
                stage="composition",
                error_type="RuntimeError",
                message="broken wiring",
            ),
        )

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])

    assert exit_code == 1


def test_main_maps_keyboard_interrupt_to_exit_code_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        raise KeyboardInterrupt

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])

    assert exit_code == 1


def test_dpost_entrypoint_delegates_to_v2_main(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        captured["request_mode"] = request.mode
        _ = emit_event
        return entrypoint.BootstrapResult(is_success=True)

    monkeypatch.setattr(entrypoint, "run", _run)

    exit_code = dpost_entrypoint.main([])

    assert exit_code == 0
    assert captured["request_mode"] == "v2"
