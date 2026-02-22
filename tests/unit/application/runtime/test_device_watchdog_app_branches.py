"""Residual branch coverage for DeviceWatchdogApp error/retry paths."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from dpost.application.interactions import ErrorMessages
from dpost.application.runtime.device_watchdog_app import DeviceWatchdogApp


def test_process_next_event_swallows_processing_exceptions(watchdog_app) -> None:
    """Log processing exceptions without crashing the event loop."""
    watchdog_app.event_queue.put("C:/tmp/fail.txt")
    watchdog_app.file_processing.process_item = MagicMock(
        side_effect=RuntimeError("boom")
    )

    watchdog_app._process_next_event()

    assert watchdog_app.event_queue.empty()


def test_handle_exception_marks_failed_session_and_shows_error(
    watchdog_app,
    fake_ui,
) -> None:
    """Record failure state, surface UI error, and trigger shutdown flow."""
    watchdog_app.on_closing = MagicMock()

    watchdog_app.handle_exception(RuntimeError, RuntimeError("boom"), None)

    assert watchdog_app._session_failed is True
    assert fake_ui.errors
    title, _message = fake_ui.errors[-1]
    assert title == ErrorMessages.APPLICATION_ERROR
    watchdog_app.on_closing.assert_called_once()


def test_collect_total_processed_returns_zero_when_registry_collection_fails(
    watchdog_app,
    monkeypatch,
) -> None:
    """Fallback to zero when prometheus registry cannot be collected."""
    monkeypatch.setattr(
        "prometheus_client.REGISTRY",
        SimpleNamespace(collect=lambda: (_ for _ in ()).throw(RuntimeError("bad"))),
    )

    assert watchdog_app._collect_total_processed() == 0


def test_schedule_retry_clips_negative_delay_to_floor(watchdog_app) -> None:
    """Clamp retry scheduling delay to minimum floor and schedule enqueue callback."""
    scheduled: list[int] = []

    def fake_schedule(delay_ms: int, callback):
        scheduled.append(delay_ms)
        assert callable(callback)
        return 1

    watchdog_app.scheduler.schedule = fake_schedule

    watchdog_app._schedule_retry("C:/tmp/retry.txt", -5.0)

    assert scheduled == [100]


def test_initialize_invokes_explicit_startup_sync_on_file_processor(
    watchdog_app,
) -> None:
    """Initialization should trigger the file-processing startup sync hook once."""
    watchdog_app.initialize()

    assert watchdog_app.file_processing.startup_sync_calls == 1


def test_run_routes_initialize_exceptions_through_handle_exception(
    watchdog_app,
    monkeypatch,
) -> None:
    """Startup failures during initialize() should use the app exception path."""
    monkeypatch.setattr(watchdog_app, "initialize", MagicMock(side_effect=RuntimeError("boom")))
    watchdog_app.handle_exception = MagicMock()

    watchdog_app.run()

    watchdog_app.handle_exception.assert_called_once()


def test_constructor_injects_dynamic_session_timeout_provider(
    config_service,
    fake_ui,
    fake_sync,
) -> None:
    """App should inject a config-backed timeout provider into SessionManager."""
    captured: dict[str, object] = {}

    class _CaptureSessionManager:
        def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            captured["kwargs"] = kwargs

    class _NoopFileProcessManager:
        def __init__(self, **_kwargs) -> None:  # type: ignore[no-untyped-def]
            pass

    app = DeviceWatchdogApp(
        ui=fake_ui,
        sync_manager=fake_sync,
        config_service=config_service,
        session_manager_cls=_CaptureSessionManager,
        file_process_manager_cls=_NoopFileProcessManager,
    )

    timeout_provider = captured["kwargs"]["timeout_provider"]
    assert callable(timeout_provider)
    assert timeout_provider() == config_service.current.session_timeout

    config_service.pc.session.timeout_seconds = 123
    assert timeout_provider() == 123
    assert app.session_manager is not None
