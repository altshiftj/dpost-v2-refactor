# dpost Architecture Tightening Checklist

## Section: Cross-cutting Documentation Governance
- Why this matters: Architectural quality degrades quickly when decisions and ownership boundaries are not documented as changes land.

### Checklist
- [ ] Keep `docs/architecture/architecture-baseline.md` aligned with current structure.
- [ ] Keep `docs/architecture/responsibility-catalog.md` aligned with ownership changes.
- [ ] Add or update ADR entries in `docs/architecture/adr/` for major architectural decisions.
- [ ] Add/update project-defined terms in `GLOSSARY.csv` when vocabulary changes.
- [ ] Link architecture-affecting PRs to relevant plan/checklist/report/ADR docs.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 1 Baseline and Contract Freeze
- Why this matters: Stable migration requires a locked behavioral baseline and clear dependency rules before refactoring.

### Checklist
- [x] Confirm full baseline test pass.
- [x] Add or verify characterization test for bootstrap startup path.
- [x] Add or verify characterization test for plugin load by canonical name.
- [x] Add or verify characterization test for processing pipeline happy path.
- [x] Add or verify characterization test for immediate sync behavior for processed records.
- [x] Add architecture contract doc describing allowed dependency directions.
- [x] Link contract doc from developer-facing documentation.

### Completion Notes
- How it was done: Closed Phase 1 on 2026-02-18 by verifying existing
  characterization coverage and running marker-specific gate suites.
  `python -m pytest -m legacy` passed (`288 passed, 4 skipped, 4 deselected`)
  and `python -m pytest -m migration` passed (`4 passed, 292 deselected`).
  Bootstrap startup characterization is covered by
  `tests/unit/core/app/test_bootstrap.py::test_bootstrap_starts_services`.
  Canonical plugin-name loading is covered by
  `tests/unit/plugin_system/test_plugin_loader.py` via
  `load_device("test_device")` and `load_pc("test_pc")`.
  Processing happy path and immediate sync behavior are covered by
  `tests/integration/test_multi_processor_app_flow.py::test_multi_processor_app_flow`
  and `tests/integration/test_device_integrations.py` assertions on
  `sync.synced_records`. Dependency direction rules are documented in
  `docs/architecture/architecture-contract.md` and linked from
  `docs/architecture/README.md`.

---

## Section: Phase 2 dpost Spine and Headless Composition Root
- Why this matters: Headless-first delivery establishes an automation-safe core before UI coupling is reintroduced.

### Checklist
- [x] Create new `dpost` package skeleton with explicit layers.
- [x] Implement a single composition root for dependency wiring.
- [x] Add a new headless `dpost` entrypoint wired through composition root.
- [x] Keep legacy entrypoint operational during transition.
- [x] Add smoke test for new headless entrypoint startup.

### Completion Notes
- How it was done: Added `src/dpost` scaffolding (`domain`, `application`,
  `infrastructure`, `plugins`, `runtime`), wired `dpost` script in
  `pyproject.toml`, added `tests/migration/test_dpost_main.py`, and validated
  with marker-aware pytest runs.

---

## Section: Phase 3 Framework Kernel and Sync Adapter Contract
- Why this matters: Establishing framework contracts first avoids coupling migration behavior to concrete integrations too early.

### Checklist
- [x] Define framework kernel boundary and port contracts for pluggable integrations.
- [x] Add framework-level migration tests that do not depend on concrete backend integrations.
- [x] Add reference sync adapter implementation (noop/local) for kernel validation.
- [x] Add reference plugin flow for kernel validation.
- [x] Define and document sync adapter port contract.
- [x] Add adapter selection mechanism to startup config.
- [x] Add startup test without Kadi adapter installed.
- [x] Add startup test for clear error path when adapter name is unknown.
- [x] Move Kadi sync behind adapter implementation boundary after kernel tests are green.
- [x] Make Kadi adapter optional in dependency/packaging flow.
- [x] Add startup test with Kadi adapter selected.

### Completion Notes
- How it was done: In progress as of 2026-02-18. Added sync kernel contract
  surface at `src/dpost/application/ports/sync.py`, reference adapter
  `src/dpost/infrastructure/sync/noop.py`, and explicit adapter selection in
  `src/dpost/runtime/composition.py` via `DPOST_SYNC_ADAPTER` (default:
  `noop`). Added migration tests in
  `tests/migration/test_sync_adapter_selection.py` and validated:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  -> `3 passed`.
- Tests-first startup wiring increment (pending implementation approval):
  added failing expectations for `compose_bootstrap` adapter-factory wiring and
  unknown-adapter env handling in
  `tests/migration/test_sync_adapter_selection.py`, plus unknown-adapter main
  exit behavior in `tests/migration/test_dpost_main.py`.
  Red-state verification run:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_dpost_main.py`
  -> `3 failed, 7 passed`.
- Startup wiring implementation increment (green):
  `src/dpost/runtime/composition.py` now resolves adapter selection before
  bootstrap and injects `sync_manager_factory` into legacy bootstrap wiring.
  Green verification runs:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_dpost_main.py`
  -> `10 passed`.
  `python -m pytest -m migration`
  -> `10 passed, 292 deselected`.
- Tests-first Kadi adapter increment (pending implementation approval):
  added failing expectations for `DPOST_SYNC_ADAPTER=kadi` startup wiring and
  missing optional dependency error handling in
  `tests/migration/test_sync_adapter_selection.py`.
  Red-state verification run:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  -> `2 failed, 5 passed`.
- Kadi adapter implementation increment (green):
  added `src/dpost/infrastructure/sync/kadi.py` and updated
  `src/dpost/runtime/composition.py` adapter selection to support `kadi`.
  Kadi import remains lazy and missing optional dependency raises a startup
  error mentioning `kadi_apy`.
  Green verification runs:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  -> `7 passed`.
  `python -m pytest -m migration`
  -> `12 passed, 292 deselected`.
- Tests-first optional Kadi packaging increment (pending implementation
  approval):
  added migration assertions for default/noop startup behavior when Kadi
  dependency is unavailable and explicit `kadi` startup failure with clear
  optional dependency messaging in
  `tests/migration/test_sync_adapter_selection.py`, plus optional packaging
  contract coverage in `tests/migration/test_optional_kadi_packaging.py`.
  Red-state verification run:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_optional_kadi_packaging.py`
  -> `1 failed, 9 passed`.
- Optional Kadi packaging implementation increment (green):
  moved `kadi-apy` from default `[project].dependencies` to
  `[project.optional-dependencies].kadi` in `pyproject.toml`.
  Green verification runs:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_optional_kadi_packaging.py tests/migration/test_dpost_main.py`
  -> `15 passed`.
  `python -m pytest -m migration`
  -> `15 passed, 292 deselected`.
- Tests-first reference plugin flow increment (pending implementation approval):
  added migration coverage in
  `tests/migration/test_reference_plugin_flow.py` to lock the expectation that
  `DPOST_PLUGIN_PROFILE=reference` passes explicit startup settings through
  composition without concrete backend/plugin coupling.
  Red-state verification run:
  `python -m pytest tests/migration/test_reference_plugin_flow.py`
  -> `1 failed`.
- Framework kernel boundary + reference plugin flow implementation increment
  (green):
  added `src/dpost/plugins/reference.py` (`PluginProfile`,
  `REFERENCE_PLUGIN_PROFILE`) and composition profile selection/wiring in
  `src/dpost/runtime/composition.py` via `DPOST_PLUGIN_PROFILE`.
  Architecture boundary docs were updated in
  `docs/architecture/architecture-contract.md`,
  `docs/architecture/architecture-baseline.md`, and
  `docs/architecture/responsibility-catalog.md`.
  Green verification run:
  `python -m pytest -m migration`
  -> `16 passed, 292 deselected`.

---

## Section: Phase 4 Configuration Consolidation
- Why this matters: Multiple configuration sources create drift and make behavior hard to reason about across environments.

### Checklist
- [x] Inventory all runtime reads from legacy constants.
- [x] Move operational configuration reads to config schema/service path.
- [x] Remove fallback usage from operational code paths.
- [x] Add test for default config behavior.
- [x] Add test for explicit path override behavior.
- [x] Add test for environment-driven bootstrap behavior.
- [x] Update docs with the canonical configuration flow.

### Completion Notes
- How it was done: Phase 4 kickoff completed on 2026-02-18 with a
  runtime configuration read inventory in
  `docs/reports/20260218-phase4-runtime-config-read-inventory.md`.
- Tests-first increment:
  added `tests/migration/test_configuration_consolidation.py` for
  default behavior, explicit override precedence, and env-driven bootstrap
  wiring through `dpost` composition.
- Red-state verification:
  `python -m pytest -m migration`
  -> `3 failed, 16 passed, 292 deselected`.
- Green implementation increment:
  updated `src/dpost/runtime/composition.py` with
  `resolve_startup_settings()` and startup-settings wiring into
  `compose_bootstrap()`.
- Green verification:
  `python -m pytest -m migration`
  -> `19 passed, 292 deselected`.
- Tests-first fallback-removal increment:
  added failing migration tests in
  `tests/migration/test_configuration_consolidation.py` asserting
  `filesystem_utils` operational helpers fail fast without an active
  config service (`init_dirs()` implicit path and `get_record_path()`).
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 19 passed, 292 deselected`.
- Green implementation increment:
  removed legacy constants fallback from
  `src/ipat_watchdog/core/storage/filesystem_utils.py` operational
  config readers, making runtime path/naming reads config-service
  authoritative.
- Green verification:
  `python -m pytest -m migration`
  -> `21 passed, 292 deselected`.
- Tests-first naming/constants increment:
  added failing migration tests in
  `tests/migration/test_naming_constants_consolidation.py` for:
  `LocalRecord` separator parsing via active config,
  `KadiSyncManager` separator-driven identifier composition,
  and fail-fast plugin separator access when config service is unavailable.
- Red-state verification:
  `python -m pytest -m migration`
  -> `4 failed, 21 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/records/local_record.py`,
  `src/ipat_watchdog/core/sync/sync_kadi.py`,
  `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`, and
  `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py`
  to remove legacy constants usage from separator reads and use
  config-driven separator resolution.
- Green verification:
  `python -m pytest -m migration`
  -> `25 passed, 292 deselected`.
- Canonical flow doc update:
  updated `docs/architecture/architecture-baseline.md` to reflect
  config-service-authoritative operational naming/path reads and
  remaining compatibility fallback boundaries.
- Legacy regression verification increment:
  `python -m pytest -m legacy` initially surfaced 6 failing unit tests
  in plugin processors that called config-dependent helpers without
  initializing config service context.
- Test harness alignment:
  updated affected unit tests to request the existing `config_service`
  fixture in:
  `tests/unit/device_plugins/dsv_horiba/test_dsv_file_processor.py`,
  `tests/unit/device_plugins/erm_hioki/test_file_processor.py`,
  `tests/unit/device_plugins/extr_haake/test_plugin.py`,
  `tests/unit/device_plugins/psa_horiba/test_file_processor.py`, and
  `tests/unit/device_plugins/rhe_kinexus/test_file_processor.py`.
- Green verification:
  `python -m pytest -m legacy`
  -> `288 passed, 4 skipped, 25 deselected`.
- Migration re-check:
  `python -m pytest -m migration`
  -> `25 passed, 292 deselected`.
- Tests-first strict fail-fast caveat increment:
  added failing migration tests in
  `tests/migration/test_naming_constants_consolidation.py` requiring
  `LocalRecord` and `KadiSyncManager` separator resolution to fail fast
  when config service is unavailable.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 25 passed, 292 deselected`.
- Green implementation increment:
  removed remaining compatibility separator fallback defaults from
  `src/ipat_watchdog/core/records/local_record.py` and
  `src/ipat_watchdog/core/sync/sync_kadi.py`.
- Legacy alignment:
  updated unit tests that construct `LocalRecord`/sync paths without
  config initialization to request `config_service` fixture in
  `tests/unit/core/records/test_local_record.py`,
  `tests/unit/core/records/test_record_manager.py`,
  `tests/unit/core/storage/test_filesystem_utils.py`,
  `tests/unit/core/sync/test_sync_kadi.py`, and
  `tests/unit/device_plugins/sem_phenomxl2/test_file_processor.py`.
- Green verification:
  `python -m pytest -m legacy`
  -> `288 passed, 4 skipped, 27 deselected`.
- Migration re-check:
  `python -m pytest -m migration`
  -> `27 passed, 292 deselected`.

---

## Section: Phase 5 Processing Pipeline Decomposition
- Why this matters: Smaller focused services improve maintainability, test isolation, and future plugin onboarding.

### Checklist
- [x] Define stage service boundaries (resolve, stabilize, preprocess, route, persist/sync).
- [ ] Extract one stage at a time with unit tests per stage.
- [ ] Keep integration behavior stable while orchestration is split.
- [ ] Reduce direct cross-module coupling in orchestration module.
- [ ] Validate no regressions in multi-device and multi-processor integration tests.

### Completion Notes
- How it was done: Phase 5 kickoff completed on 2026-02-18 with a
  decomposition report in
  `docs/reports/20260218-phase5-processing-pipeline-decomposition-report.md`.
- Tests-first increment:
  added `tests/migration/test_processing_pipeline_stage_boundaries.py`
  to require explicit resolve/stabilize stage hooks in
  `_ProcessingPipeline` and to require `process()` delegation through those
  hooks before execution.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 27 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_resolve_device_stage()` and `_stabilize_artifact_stage()`,
  and to route `process()` through these boundaries while preserving
  existing result and rejection semantics.
- Green verification:
  `python -m pytest -m migration`
  -> `29 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first preprocess-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring an explicit `_preprocess_stage()` seam and
  `_execute_pipeline()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 29 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_preprocess_stage()` and route `_execute_pipeline()` through it
  while preserving current preprocessing result semantics.
- Green verification:
  `python -m pytest -m migration`
  -> `31 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first persist/sync-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring an explicit `_persist_and_sync_stage()` seam and ACCEPT-route
  delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 31 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_persist_and_sync_stage()` and route ACCEPT path persistence
  through that stage seam.
- Green verification:
  `python -m pytest -m migration`
  -> `33 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first route-decision-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring an explicit `_route_decision_stage()` seam and ACCEPT
  reroute handling without redispatch through `_dispatch_route()`.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 33 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_route_decision_stage()` and route ACCEPT path handling in
  `_route_with_prefix()` through `_persist_and_sync_stage()` directly.
- Green verification:
  `python -m pytest -m migration`
  -> `35 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first non-ACCEPT-route-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring an explicit `_non_accept_route_stage()` seam and non-ACCEPT
  reroute handling without redispatch through `_dispatch_route()`.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 35 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_non_accept_route_stage()` and route non-ACCEPT flows from both
  `_dispatch_route()` and `_route_with_prefix()` through that seam.
- Green verification:
  `python -m pytest -m migration`
  -> `37 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first rename-recursion-reduction increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring non-ACCEPT rename retries to avoid recursive re-entry through
  `_route_with_prefix()`.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 37 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  move rename retry evaluation in `_invoke_rename_flow()` to an iterative
  loop, preserving ACCEPT persistence, unappendable warnings, and manual
  bucket cancellation behavior without recursive `_route_with_prefix()`
  re-entry.
- Green verification:
  `python -m pytest -m migration`
  -> `39 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first rename-retry-policy-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit `_rename_retry_policy_stage()` seam extraction and
  delegation from `_invoke_rename_flow()` for unappendable warning/context
  side effects.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 39 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_rename_retry_policy_stage()` and route non-ACCEPT rename retry
  policy through this seam while preserving iterative retry behavior.
- Green verification:
  `python -m pytest -m migration`
  -> `41 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.

---

## Section: Phase 6 Plugin and Discovery Hardening
- Why this matters: Plugin reliability is central to the architecture and required for open-source trust and extensibility.

### Checklist
- [ ] Normalize plugin package hygiene (`__init__.py` naming and structure).
- [ ] Remove stale plugin directories/artifacts not representing valid source plugins.
- [ ] Reconcile plugin inventory with optional dependency groups.
- [ ] Validate plugin discovery errors and messages are actionable.
- [ ] Update or remove outdated mapping expectations in tests.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 7 Desktop Runtime Integration
- Why this matters: Desktop support should sit on top of a stable headless core to avoid reintroducing tight coupling.

### Checklist
- [ ] Keep runtime mode selection explicit in composition root.
- [ ] Ensure headless mode remains green after desktop wiring changes.
- [ ] Ensure desktop mode preserves current UI interaction behavior.
- [ ] Add/refresh smoke tests for both runtime modes.
- [ ] Document runtime mode selection and behavior differences.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 8 Final Cutover and Cleanup
- Why this matters: A clean cutover prevents long-lived dual architecture and reduces maintenance cost.

### Checklist
- [ ] Switch canonical project/package identity to `dpost` in packaging and entrypoints.
- [ ] Update docs and scripts to new canonical names.
- [ ] Remove deprecated compatibility paths after validation window.
- [ ] Execute full lint and test suite as release gate.
- [ ] Prepare migration notes for contributors and users.

### Completion Notes
- How it was done: Pending.

---

## Section: Manual Check
- Why this matters: Human verification confirms real operator workflows beyond automated test coverage.

### Checklist
- [ ] Desktop manual check: app starts cleanly.
- [ ] Desktop manual check: file appears in watch directory and is processed.
- [ ] Desktop manual check: rename prompt appears for invalid prefix and cancellation routes to rename bucket.
- [ ] Desktop manual check: sync errors surface clear user-facing messages.
- [ ] Headless manual check: startup succeeds with no UI dependencies.
- [ ] Headless manual check: processing and sync still execute for representative test files.
- [ ] Headless manual check: observability and metrics endpoints start and respond.
- [ ] Plugin manual check: at least one plugin per instrument family loads and processes representative input.
- [ ] Plugin manual check: invalid plugin name produces actionable error message.
- [ ] Migration hygiene manual check: old and new entrypoints match behavior during transition window.
- [ ] Migration hygiene manual check: documented commands and setup instructions work on a clean environment.

### Completion Notes
- How it was done: Pending.
