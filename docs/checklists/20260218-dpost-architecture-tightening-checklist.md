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
- [x] Extract one stage at a time with unit tests per stage.
- [x] Keep integration behavior stable while orchestration is split.
- [x] Reduce direct cross-module coupling in orchestration module.
- [x] Validate no regressions in multi-device and multi-processor integration tests.

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
- Tests-first persist-candidate-record-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam `_persist_candidate_record_stage()` and
  ACCEPT persistence delegation through that seam from
  `_persist_and_sync_stage()`.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 41 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_persist_candidate_record_stage()` on `FileProcessManager` and
  route `_persist_and_sync_stage()` persistence through it while preserving
  current output/result behavior.
- Green verification:
  `python -m pytest -m migration`
  -> `43 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first post-persist-side-effects-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam `_post_persist_side_effects_stage()` and
  `add_item_to_record()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 43 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_post_persist_side_effects_stage()` and route post-persist
  bookkeeping/metrics/immediate-sync side effects through it from
  `add_item_to_record()`.
- Green verification:
  `python -m pytest -m migration`
  -> `45 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first resolve-record-persistence-context-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam
  `_resolve_record_persistence_context_stage()` and
  `add_item_to_record()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 45 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_resolve_record_persistence_context_stage()` and route record
  resolution/path-id setup through this seam while keeping existing
  `add_item_to_record()` behavior.
- Green verification:
  `python -m pytest -m migration`
  -> `47 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first process-record-artifact-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam `_process_record_artifact_stage()` and
  `add_item_to_record()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 47 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_process_record_artifact_stage()` and route processor
  invocation/output handling through it from `add_item_to_record()`.
- Green verification:
  `python -m pytest -m migration`
  -> `49 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first notify-success-retirement increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring `FileProcessManager.add_item_to_record()` to omit the legacy
  `notify` flag and requiring `_persist_candidate_record_stage()` to call
  `add_item_to_record()` without a notify keyword argument.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 49 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  remove the legacy `notify` argument and `notify_success` side effect from
  `add_item_to_record()`, and updated ACCEPT persistence call sites to match
  the streamlined signature.
- Green verification:
  `python -m pytest -m migration`
  -> `51 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first datatype-assignment-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam `_assign_record_datatype_stage()` and
  `add_item_to_record()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 51 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_assign_record_datatype_stage()` and route datatype assignment
  through this seam from `add_item_to_record()`.
- Green verification:
  `python -m pytest -m migration`
  -> `53 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first finalize-record-output-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam `_finalize_record_output_stage()` and
  `add_item_to_record()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 53 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_finalize_record_output_stage()` and route output finalization
  (post-persist side effects + final path return) through this seam from
  `add_item_to_record()`.
- Green verification:
  `python -m pytest -m migration`
  -> `55 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Tests-first resolve-record-processor-stage increment:
  added failing migration assertions in
  `tests/migration/test_processing_pipeline_stage_boundaries.py`
  requiring explicit manager seam `_resolve_record_processor_stage()` and
  `add_item_to_record()` delegation through that seam.
- Red-state verification:
  `python -m pytest -m migration`
  -> `2 failed, 55 passed, 292 deselected`.
- Green implementation increment:
  updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_resolve_record_processor_stage()` and route processor selection
  through this seam from `add_item_to_record()`, preserving legacy
  no-processor exception routing behavior.
- Green verification:
  `python -m pytest -m migration`
  -> `57 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Phase 5 closeout regression verification:
  `python -m pytest tests/integration/test_multi_processor_app_flow.py tests/integration/test_device_integrations.py tests/integration/test_integration.py`
  -> `20 passed`.
  `python -m pytest -m legacy`
  -> `288 passed, 4 skipped, 57 deselected`.
- Gate close summary:
  Phase 5 gate closed on 2026-02-19 after 15 decomposition increments with
  migration, targeted unit, integration, and legacy regression suites green.

---

## Section: Phase 6 Plugin and Discovery Hardening
- Why this matters: Plugin reliability is central to the architecture and required for open-source trust and extensibility.

### Checklist
- [x] Normalize plugin package hygiene (`__init__.py` naming and structure).
- [x] Remove stale plugin directories/artifacts not representing valid source plugins.
- [x] Reconcile plugin inventory with optional dependency groups.
- [x] Validate plugin discovery errors and messages are actionable.
- [x] Update or remove outdated mapping expectations in tests.

### Completion Notes
- How it was done: Phase 6 kickoff started on 2026-02-19 with plugin/discovery
  inventory report:
  `docs/reports/20260219-phase6-plugin-discovery-hardening-inventory.md`.
- Tests-first increment:
  added failing migration tests in
  `tests/migration/test_plugin_discovery_hardening.py` covering:
  plugin init hygiene, stale plugin directories, optional dependency inventory
  alignment, built-in discovery parity with source inventory, and actionable
  unknown-plugin error messaging.
- Red-state verification:
  `python -m pytest tests/migration/test_plugin_discovery_hardening.py`
  -> `5 failed`.
- First implementation increment (green):
  renamed misnamed plugin package init modules:
  `src/ipat_watchdog/device_plugins/erm_hioki/__init__.py`,
  `src/ipat_watchdog/pc_plugins/eirich_blb/__init__.py`,
  `src/ipat_watchdog/pc_plugins/hioki_blb/__init__.py`,
  `src/ipat_watchdog/pc_plugins/kinexus_blb/__init__.py`;
  removed stale directory `src/ipat_watchdog/device_plugins/psa_camsizer/`;
  and updated plugin discovery errors in
  `src/ipat_watchdog/plugin_system.py` to include available plugin names for
  actionable unknown-plugin guidance.
- Green verification:
  `python -m pytest tests/migration/test_plugin_discovery_hardening.py`
  -> `5 passed`.
  `python -m pytest -m migration`
  -> `62 passed, 292 deselected`.
  `python -m pytest tests/unit/plugin_system/test_plugin_loader.py tests/unit/device_plugins/test_device_loader.py tests/unit/pc_plugins/test_pc_plugins.py`
  -> `11 passed, 1 skipped`.
- Tests-first outdated-mapping increment:
  added failing migration guard
  `test_unit_mapping_tests_do_not_reference_legacy_plugin_ids` in
  `tests/migration/test_plugin_discovery_hardening.py` to block stale
  `twinscrew_blb`/`etr_twinscrew` references in unit mapping tests.
- Red-state verification:
  `python -m pytest tests/migration/test_plugin_discovery_hardening.py::test_unit_mapping_tests_do_not_reference_legacy_plugin_ids`
  -> `1 failed`.
- Mapping cleanup implementation (green):
  updated canonical PC mapping expectations in
  `tests/unit/loader/test_pc_device_mapping.py` and
  `tests/unit/pc_plugins/test_pc_plugins.py`, removing stale legacy IDs and
  skip-based fallback behavior for in-repo PC plugins.
- Green verification:
  `python -m pytest tests/migration/test_plugin_discovery_hardening.py::test_unit_mapping_tests_do_not_reference_legacy_plugin_ids tests/unit/loader/test_pc_device_mapping.py tests/unit/pc_plugins/test_pc_plugins.py`
  -> `27 passed`.
  `python -m pytest -m migration`
  -> `63 passed, 302 deselected`.

---

## Section: Phase 7 Desktop Runtime Integration
- Why this matters: Desktop support should sit on top of a stable headless core to avoid reintroducing tight coupling.

### Checklist
- [x] Keep runtime mode selection explicit in composition root.
- [x] Ensure headless mode remains green after desktop wiring changes.
- [x] Ensure desktop mode preserves current UI interaction behavior.
- [x] Add/refresh smoke tests for both runtime modes.
- [x] Document runtime mode selection and behavior differences.

### Completion Notes
- How it was done: Phase 7 kickoff started on 2026-02-19 with runtime-mode
  inventory report:
  `docs/reports/20260219-phase7-desktop-runtime-integration-inventory.md`.
- Tests-first increment:
  added failing migration tests in
  `tests/migration/test_runtime_mode_selection.py` covering:
  explicit runtime mode resolver behavior (`headless` default and unknown-mode
  fail-fast), explicit composition `ui_factory` wiring for both runtime modes,
  and dual runtime-mode startup smoke expectations through `dpost.main()`.
- Red-state verification:
  `python -m pytest tests/migration/test_runtime_mode_selection.py`
  -> `6 failed`.
  `python -m pytest -m migration`
  -> `6 failed, 63 passed, 302 deselected`.
- Implementation increment (green):
  updated `src/dpost/runtime/composition.py` to add explicit
  `DPOST_RUNTIME_MODE` resolution and mode-specific UI factory wiring
  (`HeadlessRuntimeUI` for headless, `TKinterUI` for desktop), and added
  `src/dpost/infrastructure/runtime/headless_ui.py`.
- Green verification:
  `python -m pytest tests/migration/test_runtime_mode_selection.py`
  -> `6 passed`.
  `python -m pytest -m migration`
  -> `69 passed, 302 deselected`.
- Desktop parity characterization increment (green):
  extended `tests/migration/test_runtime_mode_selection.py` with desktop-mode
  bootstrap/adapter behavior assertions using a desktop UI probe to lock:
  `UiInteractionAdapter` + `UiTaskScheduler` wiring and dialog/scheduler
  behavior delegation through desktop runtime composition.
- Runtime mode documentation increment:
  updated `README.md` with `DPOST_RUNTIME_MODE` selection behavior and related
  migration startup env variables.
- Green verification:
  `python -m pytest tests/migration/test_runtime_mode_selection.py`
  -> `8 passed`.
  `python -m pytest -m migration`
  -> `71 passed, 302 deselected`.
- Gate close summary:
  Phase 7 gate closed on 2026-02-19 after explicit runtime mode composition,
  dual-mode smoke tests, desktop interaction parity characterization, and
  runtime mode behavior documentation updates.

---

## Section: Phase 8 Final Cutover and Cleanup
- Why this matters: A clean cutover prevents long-lived dual architecture and reduces maintenance cost.

### Checklist
- [x] Switch canonical project/package identity to `dpost` in packaging and entrypoints.
- [x] Update docs and scripts to new canonical names.
- [ ] Remove deprecated compatibility paths after validation window.
- [x] Execute full lint and test suite as release gate.
- [x] Prepare migration notes for contributors and users.

### Completion Notes
- How it was done: Phase 8 kickoff started on 2026-02-19 with cutover
  inventory report:
  `docs/reports/20260219-phase8-final-cutover-cleanup-inventory.md`.
- Tests-first increment:
  added failing migration tests in
  `tests/migration/test_phase8_cutover_identity.py` covering:
  canonical `dpost` packaging/entrypoint identity expectations,
  docs/scripts naming cutover expectations, and legacy compatibility
  retirement guards (remove or explicitly sunset deprecated paths).
- Red-state verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `8 failed`.
  `python -m pytest -m migration`
  -> `8 failed, 71 passed, 302 deselected`.
- Implementation increment (green):
  updated canonical package/entrypoint metadata in `pyproject.toml`,
  updated startup naming in `README.md`, `USER_README.md`, and
  `DEVELOPER_README.md`, updated consolidated pipeline naming references in
  `scripts/infra/windows/consolidated_pipelines/`, and introduced
  `src/dpost/runtime/bootstrap.py` bridge wiring used by
  `src/dpost/__main__.py` and `src/dpost/runtime/composition.py`.
- Legacy compatibility-path guard alignment:
  added explicit deprecation + sunset notice in
  `src/ipat_watchdog/__main__.py` (sunset `2026-06-30`) while retaining
  transition-time compatibility.
- Runtime test stability follow-up (green):
  updated bootstrap bridge symbol resolution to lazy per-call lookup to avoid
  runtime-mode migration test hangs/timeouts under monkeypatched startup paths.
- Green verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `8 passed`.
  `python -m pytest tests/migration/test_runtime_mode_selection.py`
  -> `8 passed`.
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  -> `9 passed`.
  `python -m pytest -m migration`
  -> `79 passed, 302 deselected`.
- Migration notes increment:
  added `docs/reports/20260219-phase8-cutover-migration-notes.md` and linked it
  from `README.md`, `USER_README.md`, and `DEVELOPER_README.md`.
- Full release gate execution:
  `python -m pytest`
  -> `380 passed, 1 skipped`.
  `python -m ruff check .`
  -> `All checks passed!`.
  `python -m black --check .`
  -> `All done! 31 files would be left unchanged.`
- Formatting gate scope alignment:
  added `[tool.black]` cutover-phase temporary `extend-exclude` scope in
  `pyproject.toml` to keep Black enforcement on active migration surfaces while
  legacy compatibility paths remain in retention window.
- Post-sunset retirement planning increment:
  added dedicated retirement planning/checklist docs for compatibility path
  sunset execution:
  `docs/planning/20260219-post-sunset-compatibility-retirement-plan.md` and
  `docs/checklists/20260219-post-sunset-compatibility-retirement-checklist.md`.
- Full-strangler continuation planning increment:
  added post-Phase 8 forward plan/checklist docs:
  `docs/planning/20260219-dpost-phase9-13-full-strangler-plan.md` and
  `docs/checklists/20260219-dpost-phase9-13-full-strangler-checklist.md`.
- Phase 9 tests-first kickoff:
  added `tests/migration/test_phase9_native_bootstrap_boundary.py` and captured
  red-state inventory in
  `docs/reports/20260219-phase9-native-bootstrap-boundary-inventory.md`.
- Red-state verification:
  `python -m pytest tests/migration/test_phase9_native_bootstrap_boundary.py`
  -> `2 failed`.
- Post-sunset retirement execution kickoff (2026-02-20):
  began compatibility-path retirement with tests-first increments in
  `tests/migration/test_phase8_cutover_identity.py` and
  `tests/migration/test_dpost_main.py`.
- Retirement red/green verification snapshots:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `1 failed, 7 passed` (red after strict-removal assertion), then
  `8 passed` (green after removing `src/ipat_watchdog/__main__.py`).
  `python -m pytest tests/migration/test_dpost_main.py`
  -> `2 failed, 5 passed` (red for transition-helper removal), then
  `7 passed` (green after simplifying `src/dpost/runtime/bootstrap.py`
  and `src/dpost/__main__.py`).
- Additional sunset increment (plugin hint alignment):
  added a failing migration assertion for canonical install hint text in
  `tests/migration/test_phase8_cutover_identity.py` and updated
  `src/ipat_watchdog/plugin_system.py` install guidance from
  `pip install ipat-watchdog[...]` to `pip install dpost[...]`.
  Verification:
  `python -m pytest tests/migration/test_phase8_cutover_identity.py`
  -> `1 failed, 8 passed` (red), then `9 passed` (green).

---

## Section: Manual Check
- Why this matters: Human verification confirms real operator workflows beyond automated test coverage.

### Checklist
- [x] Desktop manual check: app starts cleanly.
- [x] Desktop manual check: file appears in watch directory and is processed.
- [x] Desktop manual check: rename prompt appears for invalid prefix and cancellation routes to rename bucket.
- [x] Desktop manual check: sync errors surface clear user-facing messages.
- [x] Headless manual check: startup succeeds with no UI dependencies.
- [x] Headless manual check: processing and sync still execute for representative test files.
- [x] Headless manual check: observability and metrics endpoints start and respond.
- [x] Plugin manual check: at least one plugin per instrument family loads and processes representative input.
- [x] Plugin manual check: invalid plugin name produces actionable error message.
- [x] Migration hygiene manual check: documented commands and setup instructions work on a clean environment.

### Manual Validation Steps
1. Desktop startup:
   set `PC_NAME` and run:
   `python -m dpost`
   with `DPOST_RUNTIME_MODE=desktop`; confirm app starts with no unhandled
   exception logs.
2. Desktop processing:
   drop one valid test artifact into configured `Upload` folder and confirm
   file lands in expected `Data/<INSTITUTE>/<USER>/<DEVICE?-SAMPLE>` path.
3. Desktop rename flow:
   drop one invalidly named artifact, confirm rename dialog appears, cancel,
   and confirm file moves to `00_To_Rename`.
4. Desktop sync error surfacing:
   run with intentionally invalid sync credentials, process one file, and
   confirm user-facing error plus log evidence.
5. Headless startup:
   run `python -m dpost` with `DPOST_RUNTIME_MODE=headless`; confirm startup
   succeeds without Tkinter/runtime UI dependency errors.
6. Headless processing/sync:
   process representative files in headless mode and confirm routing + sync
   path behavior matches expected outcomes.
7. Headless observability:
   verify metrics and observability endpoints on the configured ports:
   `http://localhost:<PROMETHEUS_PORT>/` and
   `http://localhost:<OBSERVABILITY_PORT>/health`
   (for example `9400` and `9401` in manual parity runs).
8. Plugin family spot checks:
   run at least one representative plugin per instrument family and verify
   successful load + processing path.
9. Invalid plugin actionability:
   run with an invalid plugin name and confirm error message lists available
   plugin names.
10. Setup command verification:
    validate documented install/run commands from a clean environment using
    current `README.md`, `USER_README.md`, and `DEVELOPER_README.md`.

### Completion Notes
- How it was done: Manual validation updates captured on 2026-02-20 with
  `PC_NAME=tischrem_blb`, `DEVICE_PLUGINS=sem_phenomxl2`,
  `DPOST_RUNTIME_MODE=headless`, `DPOST_SYNC_ADAPTER=kadi`, and explicit
  metrics/observability ports `9400`/`9401`.
- Historical transition-window parity evidence (captured before compatibility
  retirement):
  both `python -m ipat_watchdog` and `python -m dpost` started cleanly with
  matching startup behavior, matching plugin resolution (`tischrem_blb`,
  `sem_phenomxl2`), and matching endpoint startup logs.
- Headless endpoint evidence:
  startup logs confirmed
  `Prometheus metrics server listening on port 9400` and
  `Observability server listening on port 9401`.
- Desktop sync-error surfacing evidence:
  manual desktop run with intentionally invalid sync credentials confirmed a
  user-facing error and corresponding log evidence for failed sync.
