"""Immediate-sync error side-effect emission helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dpost.application.interactions import ErrorMessages


@dataclass(frozen=True)
class ImmediateSyncErrorEmissionSink:
    """Injectable sink callables used to emit immediate-sync error side effects."""

    log_exception: Callable[[str, Exception], None]
    show_error: Callable[[str, str], None]


def emit_immediate_sync_error(
    src_path: str,
    exc: Exception,
    sink: ImmediateSyncErrorEmissionSink,
) -> None:
    """Emit logging and user-facing error side effects for immediate-sync failures."""
    sink.log_exception(src_path, exc)
    sink.show_error(
        ErrorMessages.SYNC_ERROR,
        ErrorMessages.SYNC_ERROR_DETAILS.format(
            filename=Path(src_path).name,
            error=exc,
        ),
    )
