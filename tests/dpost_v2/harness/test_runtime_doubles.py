from __future__ import annotations

from tests.dpost_v2._support.runtime_doubles import (
    build_recording_factories,
    make_lifecycle_adapter,
)


def test_build_recording_factories_tracks_call_order() -> None:
    call_log: list[str] = []
    factories = build_recording_factories(
        ("storage", "sync"),
        call_log=call_log,
    )

    storage_adapter = factories["storage"]()
    sync_adapter = factories["sync"]()

    assert call_log == ["storage", "sync"]
    assert storage_adapter["port"] == "storage"
    assert sync_adapter["port"] == "sync"


def test_make_lifecycle_adapter_supports_shutdown_hook() -> None:
    call_log: list[str] = []
    adapter = make_lifecycle_adapter(
        "plugins",
        call_log=call_log,
        hook_name="shutdown",
    )

    adapter.shutdown()

    assert call_log == ["plugins"]


def test_make_lifecycle_adapter_supports_close_hook() -> None:
    call_log: list[str] = []
    adapter = make_lifecycle_adapter(
        "ui",
        call_log=call_log,
        hook_name="close",
    )

    adapter.close()

    assert call_log == ["ui"]
