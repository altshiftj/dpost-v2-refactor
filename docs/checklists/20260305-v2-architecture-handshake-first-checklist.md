# Checklist: V2 Architecture Handshake-First

## Execution Order (Start Here)
- Why this matters: Keep momentum by fixing core wiring seams before repeating manual baseline work.

### Manual Check
- [x] Baseline report `docs/reports/20260305-v2-standalone-runtime-ceiling-report.md` is accepted as current lock.

### Checklist
- [x] Start implementation with:
  - `Section: Concrete dependency binding handshake (TDD)`
  - `Section: Composition-to-runtime handshake (TDD)`
- [x] Defer full baseline re-run unless environment/runtime assumptions changed.

### Completion Notes
- How it was done: Re-used the March 5, 2026 standalone ceiling report as the baseline lock and started directly with red tests for concrete bindings and composed runtime side effects.

---

## Section: Baseline freeze
- Why this matters: Prevent drift while wiring architecture seams and preserve a known reference point.

### Manual Check
- [ ] `git status --short --branch` is captured in notes.
- [ ] Runtime ceiling baseline is captured (standalone run + artifact side effects).

### Checklist
- [ ] Confirm active branch and cleanliness expectations for this lane.
- [ ] Re-use `docs/reports/20260305-v2-standalone-runtime-ceiling-report.md` as baseline lock for this lane.
- [ ] Re-run standalone ceiling probe only if environment/runtime assumptions changed.
- [ ] Record exact command outputs and probe root paths.

### Completion Notes
- How it was done:

---

## Section: Startup handshake wiring (TDD)
- Why this matters: All downstream runtime behavior depends on startup payload, dependency resolution, and launch contracts.

### Manual Check
- [x] `tests/dpost_v2/test___main__.py` remains green.
- [x] `tests/dpost_v2/application/startup` remains green after seam changes.

### Checklist
- [ ] Add failing tests for settings-to-dependencies handshake (mode/profile/backends/provenance).
- [ ] Add failing tests for strict startup failure mapping by stage (`settings`, `dependencies`, `composition`, `launch`).
- [ ] Implement minimal wiring so startup emits stable diagnostics and runtime handle contract remains strict.

### Completion Notes
- How it was done: Startup settings now pass paths and backend context into dependency resolution, and the startup/application suites stayed green after the resolver stopped returning placeholder dicts for live headless wiring.

---

## Section: Concrete dependency binding handshake (TDD)
- Why this matters: Dict placeholders hide integration gaps and prevent real runtime behavior.

### Manual Check
- [x] Composition diagnostics show concrete binding types for plugin host, filesystem/file ops, record store, sync.
- [x] No implicit fallback-only path is used in default standalone wiring.

### Checklist
- [x] Add failing tests that assert concrete adapter binding types in `tests/dpost_v2/runtime/test_composition.py`.
- [x] Add failing tests in `tests/dpost_v2/runtime/test_startup_dependencies.py` for concrete factory outputs.
- [x] Implement minimal dependency factory wiring in `src/dpost_v2/runtime/startup_dependencies.py`.

### Completion Notes
- How it was done: Added red tests for concrete `ui/storage/filesystem/sync/plugins` bindings, then wired `startup_dependencies.py` to build `HeadlessUiAdapter`, `SqliteRecordStoreAdapter`, `LocalFileOpsAdapter`, initialized sync adapters, and an activated builtin `PluginHost`.

---

## Section: Composition-to-runtime handshake (TDD)
- Why this matters: Runtime success must imply a real composed application graph, not tolerant fallback behavior.

### Manual Check
- [x] Non-dry-run headless processes deterministic events and produces expected side effects in temp workspace.
- [x] Failing port bindings fail fast with explicit composition errors.

### Checklist
- [x] Add failing tests for strict port protocol conformance and disallow silent fallback to default plugin/device.
- [x] Add failing test proving file movement and record save side effects occur in composed runtime path.
- [x] Implement minimal composition changes in `src/dpost_v2/runtime/composition.py`.

### Completion Notes
- How it was done: Added red runtime tests for real plugin resolution and file movement, then updated composition to save/update real sqlite record payloads, treat `queued` and `skipped_noop` sync outcomes as non-failures, and keep the runtime on the concrete adapter path.
- Manual probe note: Stock prod config still defers fresh files at stabilize; a temporary `retry_delay_seconds = 0.0` override proved the same composed runtime moves files and persists records with `psa_horiba`, `sem_phenomxl2`, and `utm_zwick`.
- Follow-on slice note: Runtime now feeds real file mtime/size facts into stabilize and defaults settle delay to `0.0` unless explicitly configured, so stock prod headless processes fresh `.ngb`, `.tif`, and `.zs2` files in one pass.

---

## Section: Plugin policy handshake (PC scope first) (TDD)
- Why this matters: Workstation policy ownership must sit in PC plugins before device functionality migration.

### Manual Check
- [x] Selected PC plugin(s) and active device plugin scope are visible in diagnostics/events.
- [x] Out-of-scope device plugins are rejected deterministically.

### Checklist
- [x] Add failing tests for PC-scoped device selection (horiba/tischrem/zwick scope expectations).
- [x] Add failing tests for host activation + policy enforcement surfaces.
- [x] Implement minimal runtime policy wiring using plugin host/profile selection.

### Completion Notes
- How it was done:
  - Added red tests in:
    - `tests/dpost_v2/application/startup/test_settings_schema.py`
    - `tests/dpost_v2/application/startup/test_settings_service.py`
    - `tests/dpost_v2/plugins/test_host.py`
    - `tests/dpost_v2/runtime/test_composition.py`
  - Introduced explicit startup plugin-policy settings:
    - optional `plugins.pc_name`
    - optional `plugins.device_plugins`
  - Wired settings-service environment resolution for:
    - `DPOST_PC_NAME` with `PC_NAME` fallback
    - `DPOST_DEVICE_PLUGINS` with `DEVICE_PLUGINS` fallback
  - Added `PluginHost.resolve_device_scope_for_pc(...)` so workstation scope is derived from the PC plugin's validated `active_device_plugins` settings.
  - Updated composition/runtime to:
    - expose `selected_pc_plugin`, `scoped_device_plugins`, and `pc_scope_applied` in diagnostics
    - enforce scoped device selection only when a PC plugin is explicitly selected
    - reject out-of-scope candidates deterministically at resolve time
  - Deliberate compatibility choice:
    - if no workstation PC is declared, runtime keeps existing profile-wide device selection instead of introducing a new hard startup failure in this slice.

---

## Section: Ingestion handshake (processor contract path) (TDD)
- Why this matters: Functional migration later depends on verified processor contract flow now.

### Manual Check
- [x] Runtime executes processor handshake (`prepare/can_process/process`) through ingestion path.
- [x] Stage handoff carries typed processor output into route/persist/post-persist.

### Checklist
- [x] Add failing stage/integration tests for explicit processor transform handshake.
- [x] Add failing test that rejects candidates when processor cannot process under current scope.
- [x] Implement minimal ingestion wiring to pass without changing device-specific logic.

### Completion Notes
- How it was done:
  - Added an explicit `transform` stage between `stabilize` and `route`.
  - Added red tests in:
    - `tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py`
    - `tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`
    - `tests/dpost_v2/application/ingestion/stages/test_pipeline.py`
    - `tests/dpost_v2/application/ingestion/test_engine.py`
    - `tests/dpost_v2/application/ingestion/test_pipeline_integration.py`
    - `tests/dpost_v2/runtime/test_composition.py`
  - Runtime processing context is now passed into ingestion state instead of being discarded by the runtime adapter.
  - `transform` now executes:
    - optional `prepare(...)`
    - `can_process(...)`
    - `process(...)`
    - `validate_processor_result(...)`
  - Route now derives the output filename from processor `final_path` when present.
  - Persist now includes validated `processor_result` in the saved record payload.
  - Compatibility note:
    - fallback/default runtime processor shim was updated to emit a contract-valid `datatype` so non-plugin-host composition tests still use the same seam cleanly.

---

## Section: Sync boundary handshake (TDD)
- Why this matters: Payload policy and transport side effects must remain cleanly separated.

### Manual Check
- [ ] PC plugin shapes sync payload independently of backend transport adapter.
- [ ] Sync failure behavior emits canonical events and preserves ownership boundaries.

### Checklist
- [ ] Add failing tests for PC payload shaping call site and sync backend invocation contract.
- [ ] Add failing tests for immediate sync error event emission path.
- [ ] Implement minimal post-persist wiring updates.

### Completion Notes
- How it was done:

---

## Section: End-to-end handshake closeout
- Why this matters: Confirms architecture is wired correctly before functional plugin migration begins.

### Manual Check
- [ ] Headless standalone run on temp files resolves concrete plugin ids (not `default_device`).
- [ ] Filesystem side effects are visible (`incoming` reduced, `processed` populated as expected by wiring stage).
- [ ] Runtime exits with deterministic terminal reason.

### Checklist
- [ ] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [ ] Run targeted suites for startup/runtime/ingestion/plugins.
- [ ] Run `python -m pytest -q tests/dpost_v2`.
- [ ] Publish a closeout report in `docs/reports/` with risks/deferred items.

### Completion Notes
- How it was done:
