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

---

## Section: Plugin policy handshake (PC scope first) (TDD)
- Why this matters: Workstation policy ownership must sit in PC plugins before device functionality migration.

### Manual Check
- [ ] Selected PC plugin(s) and active device plugin scope are visible in diagnostics/events.
- [ ] Out-of-scope device plugins are rejected deterministically.

### Checklist
- [ ] Add failing tests for PC-scoped device selection (horiba/tischrem/zwick scope expectations).
- [ ] Add failing tests for host activation + policy enforcement surfaces.
- [ ] Implement minimal runtime policy wiring using plugin host/profile selection.

### Completion Notes
- How it was done: Manual probe evidence now exists for both sides of the current limit. Stock prod config (`retry_delay_seconds = 1.0`) deferred all three fresh files before persist, while a temporary no-settle config moved and persisted `.ngb`, `.tif`, and `.zs2` successfully. This section remains open until the stock prod stabilize/facts seam is fixed.

---

## Section: Ingestion handshake (processor contract path) (TDD)
- Why this matters: Functional migration later depends on verified processor contract flow now.

### Manual Check
- [ ] Runtime executes processor handshake (`prepare/can_process/process`) through ingestion path.
- [ ] Stage handoff carries typed processor output into route/persist/post-persist.

### Checklist
- [ ] Add failing stage/integration tests for explicit processor transform handshake.
- [ ] Add failing test that rejects candidates when processor cannot process under current scope.
- [ ] Implement minimal ingestion wiring to pass without changing device-specific logic.

### Completion Notes
- How it was done:

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
