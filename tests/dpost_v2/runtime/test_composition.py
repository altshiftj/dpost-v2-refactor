from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Mapping

import pytest

from dpost_v2.application.contracts.ports import SyncRequest, SyncResponse
from dpost_v2.application.ingestion.engine import IngestionOutcomeKind
from dpost_v2.application.runtime.dpost_app import DPostApp
from dpost_v2.application.startup.context import LaunchMetadata, build_startup_context
from dpost_v2.application.startup.settings import (
    IngestionSettings,
    NamingSettings,
    PathSettings,
    PluginPolicySettings,
    RuntimeSettings,
    StartupSettings,
    SyncSettings,
    UiSettings,
)
from dpost_v2.infrastructure.runtime.ui.headless import HeadlessUiAdapter
from dpost_v2.infrastructure.storage.file_ops import LocalFileOpsAdapter
from dpost_v2.infrastructure.storage.record_store import SqliteRecordStoreAdapter
from dpost_v2.infrastructure.sync.noop import NoopSyncAdapter
from dpost_v2.plugins.host import PluginHost
from dpost_v2.runtime.composition import (
    CompositionBindingError,
    CompositionDuplicateBindingError,
    CompositionInitializationError,
    compose_runtime,
)
from dpost_v2.runtime.startup_dependencies import (
    StartupDependencies,
    resolve_startup_dependencies,
)


@dataclass(frozen=True)
class FakeSettings:
    mode: str = "headless"
    profile: str = "ci"


def _build_context(
    factories,
    *,
    diagnostics=None,
    selected_backends=None,
    settings: object | None = None,
):
    dependencies = StartupDependencies(
        factories=factories,
        selected_backends=selected_backends
        or {"ui": "headless", "sync": "noop", "plugins": "builtin"},
        lazy_factories=frozenset(),
        warnings=(),
        diagnostics=diagnostics or {},
        cleanup=None,
    )
    return build_startup_context(
        settings=settings or FakeSettings(),
        dependencies=dependencies,
        launch_meta=LaunchMetadata(
            requested_mode="headless",
            requested_profile="ci",
            trace_id="trace-compose",
            process_id=77,
            boot_timestamp_utc="2026-03-04T11:00:00Z",
        ),
    )


def _build_real_settings(
    tmp_path: Path,
    *,
    retry_delay_seconds: float = 0.0,
    pc_name: str | None = None,
    device_plugins: tuple[str, ...] = (),
) -> StartupSettings:
    return StartupSettings(
        runtime=RuntimeSettings(mode="headless", profile="prod"),
        paths=PathSettings(
            root=str(tmp_path),
            watch=str(tmp_path / "incoming"),
            dest=str(tmp_path / "processed"),
            staging=str(tmp_path / "tmp"),
        ),
        naming=NamingSettings(prefix="DPOST", policy="prefix_only"),
        ingestion=IngestionSettings(
            retry_limit=1,
            retry_delay_seconds=retry_delay_seconds,
        ),
        sync=SyncSettings(backend="noop", api_token=None),
        ui=UiSettings(backend="headless"),
        plugins=PluginPolicySettings(
            pc_name=pc_name,
            device_plugins=device_plugins,
        ),
    )


def _build_real_runtime_context(
    tmp_path: Path,
    *,
    retry_delay_seconds: float = 0.0,
    pc_name: str | None = None,
    device_plugins: tuple[str, ...] = (),
    dependency_overrides: Mapping[str, object] | None = None,
):
    settings = _build_real_settings(
        tmp_path,
        retry_delay_seconds=retry_delay_seconds,
        pc_name=pc_name,
        device_plugins=device_plugins,
    )

    def _override_factory(adapter: object):
        def factory() -> object:
            initialize = getattr(adapter, "initialize", None)
            if callable(initialize):
                initialize()
            return adapter

        return factory

    overrides = {
        name: _override_factory(adapter)
        for name, adapter in dict(dependency_overrides or {}).items()
    }
    dependencies = resolve_startup_dependencies(
        settings=settings.to_dependency_payload(),
        environment={},
        overrides=overrides,
    )
    return build_startup_context(
        settings=settings,
        dependencies=dependencies,
        launch_meta=LaunchMetadata(
            requested_mode="headless",
            requested_profile="prod",
            trace_id="trace-compose-real",
            process_id=88,
            boot_timestamp_utc="2026-03-05T10:00:00Z",
        ),
    )


def _write_probe_text(path: Path, payload: str, *, modified_at: float) -> Path:
    path.write_text(payload, encoding="utf-8")
    os.utime(path, (modified_at, modified_at))
    return path


def _write_probe_bytes(path: Path, payload: bytes, *, modified_at: float) -> Path:
    path.write_bytes(payload)
    os.utime(path, (modified_at, modified_at))
    return path


def _load_record_payloads(bundle) -> list[dict[str, object]]:
    database_path = Path(bundle.port_bindings["storage"].healthcheck()["path"])
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "select payload_json from records order by record_id"
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def test_composition_raises_for_missing_required_port() -> None:
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "ui": lambda: object(),
            "event_sink": lambda: object(),
        }
    )

    with pytest.raises(CompositionBindingError, match="storage"):
        compose_runtime(
            context,
            required_ports=("observability", "storage", "ui", "event_sink"),
        )


def test_composition_raises_for_duplicate_required_port() -> None:
    context = _build_context(
        factories={
            "ui": lambda: object(),
            "event_sink": lambda: object(),
            "observability": lambda: object(),
            "storage": lambda: object(),
        }
    )

    with pytest.raises(CompositionDuplicateBindingError, match="ui"):
        compose_runtime(context, required_ports=("ui", "event_sink", "ui"))


def test_composition_initializes_ports_in_deterministic_order() -> None:
    init_calls: list[str] = []

    def _factory(name: str):
        return lambda: init_calls.append(name) or {"adapter": name}

    context = _build_context(
        factories={
            "observability": _factory("observability"),
            "storage": _factory("storage"),
            "sync": _factory("sync"),
            "ui": _factory("ui"),
            "event_sink": _factory("event_sink"),
            "plugins": _factory("plugins"),
        }
    )

    bundle = compose_runtime(
        context,
        required_ports=(
            "observability",
            "storage",
            "sync",
            "ui",
            "event_sink",
            "plugins",
        ),
        app_factory=lambda bindings, _context: {
            "ports": tuple(bindings.keys()),
            "mode": _context.launch.requested_mode,
        },
    )

    assert init_calls == [
        "observability",
        "storage",
        "sync",
        "ui",
        "event_sink",
        "plugins",
    ]
    assert tuple(bundle.port_bindings) == (
        "observability",
        "storage",
        "sync",
        "ui",
        "event_sink",
        "plugins",
    )
    assert bundle.app["mode"] == "headless"


def test_composition_wraps_healthcheck_failures() -> None:
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: object(),
            "sync": lambda: object(),
            "ui": lambda: object(),
            "event_sink": lambda: object(),
            "plugins": lambda: object(),
            "clock": lambda: object(),
            "filesystem": lambda: object(),
        }
    )

    with pytest.raises(CompositionInitializationError, match="healthcheck"):
        compose_runtime(
            context,
            healthchecks=(
                lambda _bindings: (_ for _ in ()).throw(RuntimeError("boom")),
            ),
        )


def test_composition_default_factory_returns_runtime_app_surface() -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.emitted: list[object] = []

        def emit(self, event: object) -> None:
            self.emitted.append(event)

    class FixedClock:
        def now(self) -> datetime:
            return datetime(2026, 3, 4, 15, 0, tzinfo=UTC)

    event_sink = EventSinkAdapter()
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: event_sink,
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: FixedClock(),
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert isinstance(bundle.app, DPostApp)
    assert result.terminal_reason == "end_of_stream"
    assert event_sink.emitted[0]["kind"] == "runtime_started"
    assert event_sink.emitted[-1]["kind"] == "runtime_completed"


def test_composition_rejects_invalid_event_sink_binding_for_default_app() -> None:
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: object(),
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    with pytest.raises(CompositionBindingError, match="event"):
        compose_runtime(context)


def test_composition_exposes_application_port_diagnostics() -> None:
    class EventSinkAdapter:
        def emit(self, event: object) -> None:
            return None

    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: EventSinkAdapter(),
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)

    assert bundle.diagnostics["application_ports"] == (
        "clock",
        "event",
        "file_ops",
        "filesystem",
        "plugin_host",
        "record_store",
        "sync",
        "ui",
    )


def test_composition_emits_stable_runtime_diagnostics_contract() -> None:
    class EventSinkAdapter:
        def emit(self, event: object) -> None:
            return None

    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: EventSinkAdapter(),
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        },
        diagnostics={
            "backend_provenance": {
                "mode": "cli",
                "profile": "environment",
                "ui": "defaults",
                "sync": "defaults",
                "plugins": "resolver_default",
                "observability": "resolver_default",
                "storage": "resolver_default",
            }
        },
        selected_backends={
            "ui": "headless",
            "sync": "noop",
            "plugins": "builtin",
            "observability": "structured",
            "storage": "filesystem",
        },
    )

    bundle = compose_runtime(context)
    diagnostics = bundle.diagnostics

    assert diagnostics["requested_mode"] == "headless"
    assert diagnostics["requested_profile"] == "ci"
    assert diagnostics["mode"] == "headless"
    assert diagnostics["profile"] == "ci"
    assert diagnostics["plugin_backend"] == "builtin"
    assert diagnostics["plugin_visibility"] == "bound"
    assert diagnostics["plugin_port_bound"] is True
    assert diagnostics["plugin_contract_valid"] is True
    assert diagnostics["selected_backends"]["plugins"] == "builtin"
    assert diagnostics["backend_provenance"] == {
        "mode": "cli",
        "profile": "environment",
        "ui": "defaults",
        "sync": "defaults",
        "plugins": "resolver_default",
        "observability": "resolver_default",
        "storage": "resolver_default",
    }


def test_composition_default_app_consumes_ui_event_source() -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    class UiAdapter:
        def initialize(self) -> None:
            return None

        def notify(self, *, severity: str, title: str, message: str) -> None:
            return None

        def prompt(
            self, *, prompt_type: str, payload: dict[str, object]
        ) -> dict[str, object]:
            return {"accepted": True}

        def show_status(self, *, message: str) -> None:
            return None

        def shutdown(self) -> None:
            return None

        def iter_events(self):
            return (
                {
                    "event_id": "evt-ui-001",
                    "path": "/tmp/ui-file.txt",
                    "event_kind": "created",
                },
            )

    class ClockAdapter:
        def now(self) -> datetime:
            return datetime(2026, 3, 4, 16, 0, tzinfo=UTC)

    event_sink = EventSinkAdapter()
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: UiAdapter(),
            "event_sink": lambda: event_sink,
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: ClockAdapter(),
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.processed_count == 1
    assert any(event["kind"] == "ingestion_succeeded" for event in event_sink.events)
    assert event_sink.events[-1]["kind"] == "runtime_completed"


def test_composition_default_app_uses_real_ingestion_engine_pipeline() -> None:
    class EventSinkAdapter:
        def emit(self, event: object) -> None:
            return None

    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: EventSinkAdapter(),
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)
    engine = bundle.app._ingestion_engine
    outcome = engine.process(
        event={
            "event_id": "evt-real-engine-001",
            "path": "/tmp/source.txt",
            "event_kind": "created",
            "observed_at": 1.0,
        }
    )

    assert outcome.kind is IngestionOutcomeKind.SUCCEEDED
    assert outcome.final_stage_id == "post_persist"


def test_composition_shutdown_hook_is_idempotent() -> None:
    shutdown_calls: list[str] = []

    class ShutdownAdapter:
        def __init__(self, name: str) -> None:
            self._name = name
            self._called = False

        def shutdown(self) -> None:
            if self._called:
                raise RuntimeError(f"{self._name} called twice")
            self._called = True
            shutdown_calls.append(self._name)

    class CloseAdapter:
        def __init__(self, name: str) -> None:
            self._name = name
            self._called = False

        def close(self) -> None:
            if self._called:
                raise RuntimeError(f"{self._name} called twice")
            self._called = True
            shutdown_calls.append(self._name)

    context = _build_context(
        factories={
            "observability": lambda: object(),
            "ui": lambda: ShutdownAdapter("ui"),
            "event_sink": lambda: object(),
            "plugins": lambda: CloseAdapter("plugins"),
        }
    )
    bundle = compose_runtime(
        context,
        required_ports=("observability", "ui", "plugins"),
        app_factory=lambda _bindings, _context: object(),
    )

    bundle.shutdown_all()
    bundle.shutdown_all()

    assert shutdown_calls == ["plugins", "ui"]


def test_composition_headless_fallback_event_source_scans_watch_dir(
    tmp_path,
) -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    class Settings:
        mode = "headless"
        profile = "ci"

        class paths:
            watch = str(tmp_path / "incoming")
            dest = str(tmp_path / "processed")

    incoming = tmp_path / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    older_path = _write_probe_text(
        incoming / "b-file.txt",
        "b",
        modified_at=1_700_000_001.0,
    )
    newer_path = _write_probe_text(
        incoming / "a-file.txt",
        "a",
        modified_at=1_700_000_002.0,
    )
    expected_ids = []
    for path in (older_path, newer_path):
        stat = path.stat()
        expected_ids.append(
            sha256(
                f"{path.resolve()}|{float(stat.st_mtime)}".encode("utf-8")
            ).hexdigest()[:16]
        )

    event_sink = EventSinkAdapter()
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: event_sink,
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        },
        settings=Settings(),
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    processed_events = [
        event
        for event in event_sink.events
        if event.get("kind") == "runtime_event_processed"
    ]
    assert result.processed_count == 2
    assert [event["event_id"] for event in processed_events] == expected_ids


def test_composition_default_runtime_uses_concrete_dependency_bindings(
    tmp_path,
) -> None:
    context = _build_real_runtime_context(tmp_path)

    bundle = compose_runtime(context)

    assert isinstance(bundle.port_bindings["ui"], HeadlessUiAdapter)
    assert isinstance(bundle.port_bindings["storage"], SqliteRecordStoreAdapter)
    assert isinstance(bundle.port_bindings["filesystem"], LocalFileOpsAdapter)
    assert isinstance(bundle.port_bindings["sync"], NoopSyncAdapter)
    assert isinstance(bundle.port_bindings["plugins"], PluginHost)


def test_composition_default_runtime_resolves_real_plugin_id_instead_of_default_device(
    tmp_path,
) -> None:
    context = _build_real_runtime_context(tmp_path)
    incoming = Path(context.settings.paths.watch)
    incoming.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.ngb"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    outcome = bundle.app._ingestion_engine.process(
        event={
            "event_id": "evt-real-plugin-001",
            "path": str(sample),
            "event_kind": "created",
            "observed_at": 1.0,
        }
    )

    assert outcome.kind is IngestionOutcomeKind.DEFERRED_RETRY
    assert outcome.state is not None
    assert outcome.state.candidate is not None
    assert outcome.state.candidate.plugin_id == "psa_horiba"
    assert outcome.state.candidate.processor_key == "psa_horiba"


def test_composition_default_runtime_moves_file_and_persists_record(tmp_path) -> None:
    context = _build_real_runtime_context(tmp_path)
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.tif"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert sample.exists() is False
    assert (processed / "sample.tif").exists() is True


def test_composition_runtime_uses_real_file_facts_for_stabilize_and_candidate(
    tmp_path,
) -> None:
    context = _build_real_runtime_context(tmp_path, retry_delay_seconds=1.0)
    incoming = Path(context.settings.paths.watch)
    incoming.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.ngb"
    sample.write_text("payload-ngb", encoding="utf-8")
    aged_timestamp = time.time() - 5.0
    os.utime(sample, (aged_timestamp, aged_timestamp))

    bundle = compose_runtime(context)
    outcome = bundle.app._ingestion_engine.process(
        event={
            "event_id": "evt-real-facts-001",
            "path": str(sample),
            "event_kind": "created",
            "observed_at": aged_timestamp,
        }
    )

    assert outcome.kind is IngestionOutcomeKind.DEFERRED_RETRY
    assert outcome.state is not None
    assert outcome.state.candidate is not None
    assert outcome.state.candidate.size == len("payload-ngb")
    assert outcome.state.candidate.modified_at == pytest.approx(
        aged_timestamp,
        abs=1.0,
    )


def test_composition_stock_prod_headless_processes_fresh_files_in_one_pass(
    tmp_path,
) -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    event_sink = EventSinkAdapter()
    context = _build_real_runtime_context(
        tmp_path,
        retry_delay_seconds=1.0,
        device_plugins=("psa_horiba", "sem_phenomxl2", "utm_zwick"),
        dependency_overrides={"event_sink": event_sink},
    )
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)

    _write_probe_text(
        incoming / "sem-sample.tif",
        "payload-tif",
        modified_at=1_700_000_001.0,
    )
    _write_probe_bytes(
        incoming / "zwick-series.zs2",
        b"payload-zs2",
        modified_at=1_700_000_002.0,
    )
    _write_probe_bytes(
        incoming / "zwick-series.xlsx",
        b"payload-xlsx",
        modified_at=1_700_000_003.0,
    )
    _write_probe_bytes(
        incoming / "psa-bucket.ngb",
        b"payload-ngb-1",
        modified_at=1_700_000_004.0,
    )
    _write_probe_text(
        incoming / "psa-bucket.csv",
        "Probenname\tBucket Sample\nX(mm)\tValue\n",
        modified_at=1_700_000_005.0,
    )
    _write_probe_text(
        incoming / "psa-sentinel.csv",
        "Probenname;Final Sample\nX(mm);Value\n",
        modified_at=1_700_000_006.0,
    )
    _write_probe_bytes(
        incoming / "psa-sentinel.ngb",
        b"payload-ngb-2",
        modified_at=1_700_000_007.0,
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.processed_count == 7
    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert tuple(incoming.iterdir()) == ()
    assert (processed / "sem-sample.tif").exists() is True
    assert (processed / "zwick-series.xlsx").exists() is True
    assert (processed / "zwick-series.zs2").exists() is True
    assert (processed / "Final Sample-01.csv").exists() is True
    assert (processed / "Final Sample-01.zip").exists() is True
    assert (processed / "Final Sample-02.csv").exists() is True
    assert (processed / "Final Sample-02.zip").exists() is True

    payloads = _load_record_payloads(bundle)
    plugin_ids = {payload["candidate"]["plugin_id"] for payload in payloads}
    assert len(payloads) == 3
    assert plugin_ids == {"psa_horiba", "sem_phenomxl2", "utm_zwick"}

    processed_events = [
        event
        for event in event_sink.events
        if event.get("kind") == "runtime_event_processed"
    ]
    assert [event["outcome_kind"] for event in processed_events] == [
        "succeeded",
        "deferred_retry",
        "succeeded",
        "deferred_retry",
        "deferred_retry",
        "deferred_retry",
        "succeeded",
    ]


def test_composition_runtime_persists_processor_result_payload(tmp_path) -> None:
    context = _build_real_runtime_context(tmp_path, pc_name="zwick_blb")
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    _write_probe_bytes(
        incoming / "sample.zs2",
        b"payload-zs2",
        modified_at=1_700_000_001.0,
    )
    _write_probe_bytes(
        incoming / "sample.xlsx",
        b"payload-xlsx",
        modified_at=1_700_000_002.0,
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.failed_count == 0
    payloads = _load_record_payloads(bundle)

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["processor_result"]["datatype"] == "xlsx"
    assert payload["processor_result"]["final_path"].endswith("processed/sample.xlsx")
    assert payload["processor_result"]["force_paths"] == [
        str(processed / "sample.zs2").replace("\\", "/")
    ]


def test_composition_exposes_selected_pc_scope_in_diagnostics(tmp_path) -> None:
    context = _build_real_runtime_context(tmp_path, pc_name="tischrem_blb")

    bundle = compose_runtime(context)

    assert bundle.diagnostics["selected_pc_plugin"] == "tischrem_blb"
    assert bundle.diagnostics["pc_scope_applied"] is True
    assert bundle.diagnostics["scoped_device_plugins"] == ("sem_phenomxl2",)


def test_composition_runtime_rejects_candidate_outside_selected_pc_scope(
    tmp_path,
) -> None:
    context = _build_real_runtime_context(tmp_path, pc_name="tischrem_blb")
    incoming = Path(context.settings.paths.watch)
    incoming.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.ngb"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    outcome = bundle.app._ingestion_engine.process(
        event={
            "event_id": "evt-out-of-scope-001",
            "path": str(sample),
            "event_kind": "created",
            "observed_at": 1.0,
        }
    )

    assert outcome.kind is IngestionOutcomeKind.REJECTED
    assert outcome.final_stage_id == "resolve"


def test_composition_runtime_selects_allowed_device_with_selected_pc_scope(
    tmp_path,
) -> None:
    context = _build_real_runtime_context(tmp_path, pc_name="tischrem_blb")
    incoming = Path(context.settings.paths.watch)
    incoming.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.tif"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    outcome = bundle.app._ingestion_engine.process(
        event={
            "event_id": "evt-pc-scope-001",
            "path": str(sample),
            "event_kind": "created",
            "observed_at": 1.0,
        }
    )

    assert outcome.kind is IngestionOutcomeKind.SUCCEEDED
    assert outcome.state is not None
    assert outcome.state.candidate is not None
    assert outcome.state.candidate.plugin_id == "sem_phenomxl2"


def test_composition_runtime_processes_pc_scoped_sem_pair_end_to_end(
    tmp_path,
) -> None:
    context = _build_real_runtime_context(tmp_path, pc_name="tischrem_blb")
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.tif"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert sample.exists() is False
    assert (processed / "sample.tif").exists() is True

    payloads = _load_record_payloads(bundle)
    assert len(payloads) == 1
    assert payloads[0]["candidate"]["plugin_id"] == "sem_phenomxl2"


def test_composition_runtime_processes_pc_scoped_zwick_staged_pair_end_to_end(
    tmp_path,
) -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    event_sink = EventSinkAdapter()
    context = _build_real_runtime_context(
        tmp_path,
        pc_name="zwick_blb",
        dependency_overrides={"event_sink": event_sink},
    )
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    _write_probe_bytes(
        incoming / "sample.zs2",
        b"payload-zs2",
        modified_at=1_700_000_001.0,
    )
    _write_probe_bytes(
        incoming / "sample.xlsx",
        b"payload-xlsx",
        modified_at=1_700_000_002.0,
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.processed_count == 2
    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert tuple(incoming.iterdir()) == ()
    assert (processed / "sample.xlsx").exists() is True
    assert (processed / "sample.zs2").exists() is True

    payloads = _load_record_payloads(bundle)
    assert len(payloads) == 1
    assert payloads[0]["candidate"]["plugin_id"] == "utm_zwick"

    processed_events = [
        event
        for event in event_sink.events
        if event.get("kind") == "runtime_event_processed"
    ]
    assert [event["outcome_kind"] for event in processed_events] == [
        "deferred_retry",
        "succeeded",
    ]


def test_composition_runtime_processes_pc_scoped_psa_staged_batch_end_to_end(
    tmp_path,
) -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    event_sink = EventSinkAdapter()
    context = _build_real_runtime_context(
        tmp_path,
        pc_name="horiba_blb",
        dependency_overrides={"event_sink": event_sink},
    )
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    _write_probe_bytes(
        incoming / "bucket.ngb",
        b"payload-ngb-1",
        modified_at=1_700_000_001.0,
    )
    _write_probe_text(
        incoming / "bucket.csv",
        "Probenname\tBucket Sample\nX(mm)\tValue\n",
        modified_at=1_700_000_002.0,
    )
    _write_probe_text(
        incoming / "sentinel.csv",
        "Probenname;Final Sample\nX(mm);Value\n",
        modified_at=1_700_000_003.0,
    )
    _write_probe_bytes(
        incoming / "sentinel.ngb",
        b"payload-ngb-2",
        modified_at=1_700_000_004.0,
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.processed_count == 4
    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert tuple(incoming.iterdir()) == ()
    assert (processed / "Final Sample-01.csv").exists() is True
    assert (processed / "Final Sample-01.zip").exists() is True
    assert (processed / "Final Sample-02.csv").exists() is True
    assert (processed / "Final Sample-02.zip").exists() is True

    payloads = _load_record_payloads(bundle)
    assert len(payloads) == 1
    assert payloads[0]["candidate"]["plugin_id"] == "psa_horiba"

    processed_events = [
        event
        for event in event_sink.events
        if event.get("kind") == "runtime_event_processed"
    ]
    assert [event["outcome_kind"] for event in processed_events] == [
        "deferred_retry",
        "deferred_retry",
        "deferred_retry",
        "succeeded",
    ]


def test_composition_runtime_shapes_sync_payload_via_selected_pc_plugin(
    tmp_path,
) -> None:
    class CapturingSyncAdapter:
        def __init__(self) -> None:
            self.requests: list[SyncRequest] = []
            self._ready = False

        def initialize(self) -> None:
            self._ready = True

        def shutdown(self) -> None:
            self._ready = False

        def sync_record(self, request: SyncRequest) -> SyncResponse:
            assert self._ready is True
            self.requests.append(request)
            return SyncResponse(status="queued", metadata={"backend": "captured"})

    sync_adapter = CapturingSyncAdapter()
    context = _build_real_runtime_context(
        tmp_path,
        pc_name="tischrem_blb",
        dependency_overrides={"sync": sync_adapter},
    )
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.tif"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.failed_count == 0
    assert len(sync_adapter.requests) == 1
    request = sync_adapter.requests[0]
    assert request.record_id is not None
    assert request.payload == {
        "record_id": request.record_id,
        "plugin_id": "tischrem_blb",
    }


def test_composition_runtime_emits_sync_error_and_marks_record_unsynced_on_sync_failure(
    tmp_path,
) -> None:
    class FailingSyncAdapter:
        def __init__(self) -> None:
            self.requests: list[SyncRequest] = []
            self._ready = False

        def initialize(self) -> None:
            self._ready = True

        def shutdown(self) -> None:
            self._ready = False

        def sync_record(self, request: SyncRequest) -> SyncResponse:
            assert self._ready is True
            self.requests.append(request)
            return SyncResponse(status="conflict", reason_code="remote_conflict")

    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    sync_adapter = FailingSyncAdapter()
    event_sink = EventSinkAdapter()
    context = _build_real_runtime_context(
        tmp_path,
        pc_name="tischrem_blb",
        dependency_overrides={"sync": sync_adapter, "event_sink": event_sink},
    )
    incoming = Path(context.settings.paths.watch)
    processed = Path(context.settings.paths.dest)
    incoming.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    sample = incoming / "sample.tif"
    sample.write_text("payload", encoding="utf-8")

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.failed_count == 0
    assert result.terminal_reason == "end_of_stream"
    assert len(sync_adapter.requests) == 1
    assert sync_adapter.requests[0].payload["plugin_id"] == "tischrem_blb"

    sync_error_events = [
        event
        for event in event_sink.events
        if event.get("kind") == "immediate_sync_error"
    ]
    assert len(sync_error_events) == 1
    assert sync_error_events[0]["record_id"] == sync_adapter.requests[0].record_id
    assert sync_error_events[0]["reason_code"] == "remote_conflict"

    database_path = Path(bundle.port_bindings["storage"].healthcheck()["path"])
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "select payload_json from records order by record_id"
        ).fetchone()

    assert row is not None
    payload = json.loads(row[0])
    assert payload["sync_status"] == "unsynced"
