from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import dpost.__main__ as dpost_entrypoint
import dpost_v2.__main__ as entrypoint
from dpost_v2.application.startup.bootstrap import BootstrapResult, StartupFailure


class _RuntimeHandle:
    def __init__(
        self,
        *,
        terminal_reason: str = "end_of_stream",
        error: Exception | None = None,
        result: object | None = None,
        shutdown_error: Exception | None = None,
    ) -> None:
        self.terminal_reason = terminal_reason
        self.error = error
        self.result = result
        self.shutdown_error = shutdown_error
        self.calls = 0
        self.shutdown_calls = 0

    def run(self) -> object:
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result
        return SimpleNamespace(terminal_reason=self.terminal_reason)

    def shutdown(self) -> None:
        self.shutdown_calls += 1
        if self.shutdown_error is not None:
            raise self.shutdown_error


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

    exit_code = entrypoint.main(["--dry-run"])

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

    exit_code = entrypoint.main(["--dry-run"])
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


def test_main_handles_non_integer_system_exit_code_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_system_exit(_argv):  # type: ignore[no-untyped-def]
        raise SystemExit("invalid parser state")

    monkeypatch.setattr(entrypoint, "_parse_cli", _raise_system_exit)

    exit_code = entrypoint.main([])

    assert exit_code == 1


def test_dpost_entrypoint_delegates_to_v2_main(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        captured["request_mode"] = request.mode
        _ = emit_event
        return entrypoint.BootstrapResult(is_success=True)

    monkeypatch.delenv("DPOST_MODE", raising=False)
    monkeypatch.delenv("DPOST_PROFILE", raising=False)
    monkeypatch.delenv("DPOST_CONFIG", raising=False)
    monkeypatch.setattr(entrypoint, "run", _run)

    exit_code = dpost_entrypoint.main(["--dry-run"])

    assert exit_code == 0
    assert captured["request_mode"] == "v2"


def test_main_non_dry_run_executes_runtime_handle_once(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_handle = _RuntimeHandle(terminal_reason="end_of_stream")

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert runtime_handle.calls == 1
    assert runtime_handle.shutdown_calls == 1
    assert "dpost startup succeeded" in captured.out


def test_main_dry_run_does_not_execute_runtime_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_handle = _RuntimeHandle(terminal_reason="end_of_stream")

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2", "--dry-run"])

    assert exit_code == 0
    assert runtime_handle.calls == 0


def test_main_non_dry_run_fails_when_runtime_handle_missing_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=object())

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "runtime contract violation" in captured.err


def test_main_non_dry_run_fails_when_runtime_result_missing_terminal_reason(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_handle = _RuntimeHandle(result=SimpleNamespace())

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "runtime contract violation" in captured.err


@pytest.mark.parametrize(
    ("terminal_reason", "expected_exit_code"),
    [
        ("end_of_stream", 0),
        ("cancelled", 0),
        ("soft_timeout", 0),
        ("failed_terminal", 1),
        ("hard_timeout", 1),
    ],
)
def test_main_maps_runtime_terminal_reason_to_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    terminal_reason: str,
    expected_exit_code: int,
) -> None:
    runtime_handle = _RuntimeHandle(terminal_reason=terminal_reason)

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == expected_exit_code
    if expected_exit_code == 0:
        assert "dpost startup succeeded" in captured.out
    else:
        assert "dpost startup succeeded" not in captured.out


def test_main_maps_runtime_exception_to_exit_code_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_handle = _RuntimeHandle(error=RuntimeError("runtime boom"))

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert runtime_handle.shutdown_calls == 1
    assert "runtime boom" in captured.err


def test_main_invokes_runtime_shutdown_when_runtime_is_interrupted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_handle = _RuntimeHandle(error=KeyboardInterrupt())

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert runtime_handle.shutdown_calls == 1
    assert "Runtime interrupted by user." in captured.err


def test_main_non_dry_run_fails_when_runtime_shutdown_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_handle = _RuntimeHandle(
        terminal_reason="end_of_stream",
        shutdown_error=RuntimeError("shutdown boom"),
    )

    def _run(*, request, emit_event, **_kwargs):  # type: ignore[no-untyped-def]
        _ = (request, emit_event)
        return BootstrapResult(is_success=True, runtime_handle=runtime_handle)

    monkeypatch.setattr(entrypoint.startup_bootstrap, "run", _run)

    exit_code = entrypoint.main(["--mode", "v2"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert runtime_handle.calls == 1
    assert runtime_handle.shutdown_calls == 1
    assert "runtime shutdown failed" in captured.err
