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
- [x] `git status --short --branch` is captured in notes.
- [x] Runtime ceiling baseline is captured (standalone run + artifact side effects).

### Checklist
- [x] Confirm active branch and cleanliness expectations for this lane.
- [x] Re-use `docs/reports/20260305-v2-standalone-runtime-ceiling-report.md` as baseline lock for this lane.
- [x] Re-run standalone ceiling probe only if environment/runtime assumptions changed.
- [x] Record exact command outputs and probe root paths.

### Completion Notes
- How it was done:
  - Captured lane-start status before this closeout slice:
    - `git status --short --branch` -> `## main...origin/main [ahead 1]`
  - Re-used the March 5, 2026 standalone ceiling report as the baseline lock.
  - Closeout manual probes were recorded in the closeout report with exact temp probe roots under:
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\dpost-v2-closeout-7b_a28e4`

---

## Section: Startup handshake wiring (TDD)
- Why this matters: All downstream runtime behavior depends on startup payload, dependency resolution, and launch contracts.

### Manual Check
- [x] `tests/dpost_v2/test___main__.py` remains green.
- [x] `tests/dpost_v2/application/startup` remains green after seam changes.

### Checklist
- [x] Add failing tests for settings-to-dependencies handshake (mode/profile/backends/provenance).
- [x] Add failing tests for strict startup failure mapping by stage (`settings`, `dependencies`, `composition`, `launch`).
- [x] Implement minimal wiring so startup emits stable diagnostics and runtime handle contract remains strict.

### Completion Notes
- How it was done:
  - Existing bootstrap/entrypoint coverage already proves this seam in:
    - `tests/dpost_v2/application/startup/test_bootstrap.py`
    - `tests/dpost_v2/test___main__.py`
  - The closeout targeted suite revalidated:
    - stable startup diagnostics (`settings_fingerprint`, `settings_provenance`, `selected_backends`, `plugin_backend`, `plugin_visibility`)
    - strict failure stage mapping for `settings`, `composition`, and `launch`
    - strict runtime-handle and terminal-reason contract mapping at the CLI entrypoint
  - Startup settings continue to pass backend/context payloads into dependency resolution for composed headless runtime wiring.

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
- [x] PC plugin shapes sync payload independently of backend transport adapter.
- [x] Sync failure behavior emits canonical events and preserves ownership boundaries.

### Checklist
- [x] Add failing tests for PC payload shaping call site and sync backend invocation contract.
- [x] Add failing tests for immediate sync error event emission path.
- [x] Implement minimal post-persist wiring updates.

### Completion Notes
- How it was done:
  - Added red tests in:
    - `tests/dpost_v2/plugins/test_host.py`
    - `tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`
    - `tests/dpost_v2/runtime/test_composition.py`
  - Added `PluginHost.prepare_sync_payload(...)` so PC-owned payload shaping stays behind the plugin-host boundary.
  - Extended `IngestionState` and persist-stage handoff with `record_snapshot` so post-persist sync uses persisted record data instead of a hard-coded payload token.
  - Updated `run_post_persist_stage(...)` so runtime sync receives the full ingestion state, not only `record_id`.
  - Updated runtime composition to:
    - shape sync payloads through the selected PC plugin when one is explicitly selected,
    - fall back to `{record_id}` payloads when no PC plugin is selected,
    - mark persisted records `unsynced` on immediate sync failure,
    - emit canonical `immediate_sync_error` events while keeping sync backend ownership limited to transport.
  - Validation note:
    - runtime proof now shows `horiba_blb` shaping the outbound payload while the sync adapter only receives `SyncRequest`.

---

## Section: End-to-end handshake closeout
- Why this matters: Confirms architecture is wired correctly before functional plugin migration begins.

### Manual Check
- [x] Headless standalone run on temp files resolves concrete plugin ids (not `default_device`).
- [x] Filesystem side effects are visible (`incoming` reduced, `processed` populated as expected by wiring stage).
- [x] Runtime exits with deterministic terminal reason.

### Checklist
- [x] Run `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [x] Run targeted suites for startup/runtime/ingestion/plugins.
- [x] Run `python -m pytest -q tests/dpost_v2`.
- [x] Publish a closeout report in `docs/reports/` with risks/deferred items.

### Completion Notes
- How it was done:
  - Added runtime smoke proof in `tests/dpost_v2/runtime/test_composition.py` for all three workstation/device pairs:
    - `horiba_blb -> psa_horiba`
    - `tischrem_blb -> sem_phenomxl2`
    - `zwick_blb -> utm_zwick`
  - Manual installed-runtime probes confirmed for each pair:
    - concrete `plugin_id`
    - empty `incoming/`
    - expected file present in `processed/`
    - `terminal_reason='end_of_stream'`
  - Direct user CLI probes also confirmed the same matrix at:
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\dpost-v2-horiba-20260305-215159`
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\dpost-v2-tischrem-20260305-215344`
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\dpost-v2-zwick-20260305-215424`
    - persisted sqlite `candidate.plugin_id` values:
      - `psa_horiba`
      - `sem_phenomxl2`
      - `utm_zwick`
  - Validation runs:
    - `python -m ruff check src/dpost_v2 tests/dpost_v2` -> passed
    - `python -m pytest -q tests/dpost_v2/test___main__.py tests/dpost_v2/application/startup tests/dpost_v2/runtime tests/dpost_v2/application/runtime tests/dpost_v2/application/ingestion tests/dpost_v2/plugins` -> `189 passed`
    - `python -m pytest -q tests/dpost_v2` -> `412 passed`
  - Published closeout report:
    - `docs/reports/20260305-v2-handshake-closeout-report.md`
