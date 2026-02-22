"""Unit tests for immediate-sync error side-effect emission helpers."""

from __future__ import annotations

from dpost.application.interactions import ErrorMessages
from dpost.application.processing.immediate_sync_error_emitter import (
    ImmediateSyncErrorEmissionSink,
    emit_immediate_sync_error,
)


def test_emit_immediate_sync_error_logs_and_shows_formatted_error() -> None:
    """Emit log + UI error side effects with filename-specific details."""
    calls: list[tuple[str, object]] = []
    sink = ImmediateSyncErrorEmissionSink(
        log_exception=lambda src_path, exc: calls.append(("log", (src_path, str(exc)))),
        show_error=lambda title, message: calls.append(("ui", (title, message))),
    )

    emit_immediate_sync_error("C:/watch/source-file.csv", RuntimeError("sync boom"), sink)

    assert calls[0] == ("log", ("C:/watch/source-file.csv", "sync boom"))
    title, message = calls[1][1]
    assert calls[1][0] == "ui"
    assert title == ErrorMessages.SYNC_ERROR
    assert "source-file.csv" in message
    assert "sync boom" in message

