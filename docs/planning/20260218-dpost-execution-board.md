# dpost Migration Execution Board

## Board Metadata
- Created: 2026-02-18
- Planning horizon: 2026-02-18 to 2026-05-15
- Runtime posture: headless-first
- Sync posture: optional adapter model

## Owner Roles
- Core Owner: Repository maintainer driving architecture and merges.
- Plugin Owner: Maintainer handling plugin hygiene and discovery validation.
- Runtime Owner: Maintainer handling entrypoints, runtime modes, and deployment scripts.
- QA Owner: Maintainer handling gates, regression checks, and manual validation.

## Schedule
| Phase | Window (Start -> Target End) | Owner | Status | Gate to Close |
|---|---|---|---|---|
| Phase 1: Baseline and Contract Freeze | 2026-02-19 -> 2026-02-26 | QA Owner + Core Owner | Completed (2026-02-18) | Baseline tests green and architecture contract doc linked |
| Phase 2: dpost Spine and Headless Composition Root | 2026-02-27 -> 2026-03-10 | Runtime Owner + Core Owner | Completed (2026-02-18) | Headless `dpost` entrypoint smoke test green, legacy entrypoint intact |
| Phase 3: Framework Kernel and Sync Adapter Contract | 2026-03-11 -> 2026-03-19 | Core Owner | Completed (2026-02-18) | Framework contracts + reference implementations green before concrete adapter migration |
| Phase 4: Configuration Consolidation | 2026-03-20 -> 2026-03-31 | Core Owner | Completed (2026-02-18) | Legacy constant fallbacks removed from operational paths |
| Phase 5: Processing Pipeline Decomposition | 2026-04-01 -> 2026-04-15 | Core Owner | In progress (2026-02-18) | Stage services extracted, integration suite unchanged/green |
| Phase 6: Plugin and Discovery Hardening | 2026-04-16 -> 2026-04-24 | Plugin Owner | Planned | Plugin inventory normalized and discovery tests green |
| Phase 7: Desktop Runtime Integration | 2026-04-27 -> 2026-05-06 | Runtime Owner | Planned | Desktop and headless smoke tests both green |
| Phase 8: Final Cutover and Cleanup | 2026-05-07 -> 2026-05-15 | Core Owner + QA Owner | Planned | `dpost` canonical metadata/docs complete and release gate passed |

## Weekly Cadence
- Monday: phase planning and risk review.
- Wednesday: mid-phase checkpoint against gate criteria.
- Friday: gate readiness check and issue triage.
- Friday (documentation gate): verify baseline/responsibility/ADR/glossary updates for the week.

## Change Control
- Any scope change that affects a closed phase gate requires:
- explicit note in this board
- updated acceptance criteria in the phase checklist
- re-baselined target end date

## Current State (as of 2026-02-18)
- Decisions captured and locked in planning/checklist docs.
- Phase 1 gate formally closed on 2026-02-18:
- `python -m pytest -m legacy`: `288 passed, 4 skipped, 4 deselected`.
- `python -m pytest -m migration`: `4 passed, 292 deselected`.
- Contract linkage verified from `docs/architecture/README.md` to `docs/architecture/architecture-contract.md`.
- Phase 2 gate closed early on 2026-02-18:
- `src/dpost/` package skeleton exists.
- `dpost` script entrypoint exists in `pyproject.toml`.
- migration entrypoint tests exist under `tests/migration/`.
- marker split is active (`legacy` and `migration`).
- Sequencing update: Phase 3 is framework-first; concrete Kadi adapter migration follows kernel contract validation.
- Phase 3 tests-first kickoff on 2026-02-18:
- added `tests/migration/test_sync_adapter_selection.py` to lock initial kernel
  expectations for sync adapter selection/error handling.
- initial red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `3 failed` before implementation.
- post-approval implementation status:
- added `src/dpost/application/ports/sync.py` (`SyncAdapterPort`),
  `src/dpost/infrastructure/sync/noop.py` (`NoopSyncAdapter`), and
  adapter selection in `src/dpost/runtime/composition.py`.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `3 passed`.
- migration marker check:
  `python -m pytest -m migration`
  returned `7 passed, 292 deselected`.
- Phase 3 startup-wiring tests-first increment on 2026-02-18:
- added failing tests for `compose_bootstrap` sync-factory wiring and
  unknown-adapter env behavior in
  `tests/migration/test_sync_adapter_selection.py`.
- added failing test for `dpost.main()` unknown-adapter env exit path in
  `tests/migration/test_dpost_main.py`.
- red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_dpost_main.py`
  returned `3 failed, 7 passed` pending implementation.
- startup-wiring implementation status:
- `src/dpost/runtime/composition.py` now pre-validates selected adapter and
  passes `sync_manager_factory` into legacy bootstrap.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_dpost_main.py`
  returned `10 passed`.
- migration marker re-check:
  `python -m pytest -m migration`
  returned `10 passed, 292 deselected`.
- Phase 3 Kadi adapter tests-first increment on 2026-02-18:
- added failing tests for `DPOST_SYNC_ADAPTER=kadi` startup wiring and missing
  optional dependency error handling in
  `tests/migration/test_sync_adapter_selection.py`.
- red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `2 failed, 5 passed` pending implementation.
- Kadi adapter implementation status:
- added `src/dpost/infrastructure/sync/kadi.py` and updated
  `src/dpost/runtime/composition.py` to select `kadi` explicitly.
- missing optional dependency (`kadi_apy`) now raises startup error on adapter
  selection.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py`
  returned `7 passed`.
- migration marker re-check:
  `python -m pytest -m migration`
  returned `12 passed, 292 deselected`.
- Phase 3 optional Kadi packaging tests-first increment on 2026-02-18:
- added migration assertions for default/noop startup behavior when Kadi
  dependency is unavailable and explicit `kadi` startup failure messaging in
  `tests/migration/test_sync_adapter_selection.py`.
- added packaging contract coverage in
  `tests/migration/test_optional_kadi_packaging.py`.
- red-state verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_optional_kadi_packaging.py`
  returned `1 failed, 9 passed` pending implementation.
- optional Kadi packaging implementation status:
- `pyproject.toml` now keeps `kadi-apy` out of default
  `[project].dependencies` and exposes it through
  `[project.optional-dependencies].kadi`.
- green verification:
  `python -m pytest tests/migration/test_sync_adapter_selection.py tests/migration/test_optional_kadi_packaging.py tests/migration/test_dpost_main.py`
  returned `15 passed`.
- migration marker re-check:
  `python -m pytest -m migration`
  returned `15 passed, 292 deselected`.
- Phase 3 reference plugin flow tests-first increment on 2026-02-18:
- added failing migration test in
  `tests/migration/test_reference_plugin_flow.py` to assert
  `DPOST_PLUGIN_PROFILE=reference` startup wiring through composition.
- red-state verification:
  `python -m pytest tests/migration/test_reference_plugin_flow.py`
  returned `1 failed` pending implementation.
- framework kernel boundary + reference plugin flow implementation status:
- added `src/dpost/plugins/reference.py` and updated
  `src/dpost/runtime/composition.py` to support `DPOST_PLUGIN_PROFILE` with
  explicit `reference` profile mapping.
- updated architecture boundary documentation in:
  `docs/architecture/architecture-contract.md`,
  `docs/architecture/architecture-baseline.md`,
  `docs/architecture/responsibility-catalog.md`, and `GLOSSARY.csv`.
- green verification:
  `python -m pytest -m migration`
  returned `16 passed, 292 deselected`.
- Phase 3 gate closed on 2026-02-18 after kernel contracts, reference sync
  adapter, and reference plugin flow were validated together.
- Phase 4 configuration-consolidation tests-first kickoff on 2026-02-18:
- added runtime config-read inventory report:
  `docs/reports/20260218-phase4-runtime-config-read-inventory.md`.
- added migration tests in
  `tests/migration/test_configuration_consolidation.py` for:
  default resolver behavior, explicit override precedence, and env-driven
  bootstrap startup-settings wiring.
- red-state verification:
  `python -m pytest -m migration`
  returned `3 failed, 16 passed, 292 deselected`.
- Phase 4 minimal resolver/composition implementation status:
- updated `src/dpost/runtime/composition.py` with
  `resolve_startup_settings()` and `DPOST_PC_NAME`,
  `DPOST_DEVICE_PLUGINS`, `DPOST_PROMETHEUS_PORT`,
  `DPOST_OBSERVABILITY_PORT` mapping into bootstrap `StartupSettings`.
- preserved existing `DPOST_PLUGIN_PROFILE=reference` composition behavior.
- green verification:
  `python -m pytest -m migration`
  returned `19 passed, 292 deselected`.
- Phase 4 filesystem operational fallback-removal tests-first increment on
  2026-02-18:
- added failing migration tests in
  `tests/migration/test_configuration_consolidation.py` requiring
  config-service-authoritative behavior for implicit `init_dirs()` and
  `get_record_path()` resolution paths.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 19 passed, 292 deselected`.
- implementation status:
- updated `src/ipat_watchdog/core/storage/filesystem_utils.py` to remove
  legacy constants fallback from operational config readers (`_directory_list`,
  `_dest_dir`, `_rename_dir`, `_exceptions_dir`, `_daily_records_path`,
  `_id_sep`, `_file_sep`, `_filename_pattern`, `_current_device`).
- green verification:
  `python -m pytest -m migration`
  returned `21 passed, 292 deselected`.
- Phase 4 naming/constants consolidation tests-first increment on 2026-02-18:
- added failing migration tests in
  `tests/migration/test_naming_constants_consolidation.py` to verify
  active-config separator behavior for `LocalRecord` and `KadiSyncManager`,
  and fail-fast separator access in PSA/Kinexus processors when config
  service is unavailable.
- red-state verification:
  `python -m pytest -m migration`
  returned `4 failed, 21 passed, 292 deselected`.
- implementation status:
- removed legacy constants separator reads in
  `src/ipat_watchdog/core/records/local_record.py`,
  `src/ipat_watchdog/core/sync/sync_kadi.py`,
  `src/ipat_watchdog/device_plugins/psa_horiba/file_processor.py`, and
  `src/ipat_watchdog/device_plugins/rhe_kinexus/file_processor.py`.
- green verification:
  `python -m pytest -m migration`
  returned `25 passed, 292 deselected`.
- Phase 4 legacy regression validation after config-authoritative path changes:
- initial run:
  `python -m pytest -m legacy`
  returned `6 failed, 282 passed, 4 skipped, 25 deselected` from
  plugin unit tests invoking config-dependent helpers without initialized
  config service context.
- test updates:
  aligned affected unit tests to request `config_service` fixture in
  DSV Horiba, ERM Hioki, EXTR Haake, PSA Horiba, and RHE Kinexus test
  modules.
- green verification:
  `python -m pytest -m legacy`
  returned `288 passed, 4 skipped, 25 deselected`.
- migration re-check:
  `python -m pytest -m migration`
  returned `25 passed, 292 deselected`.
- Phase 4 strict fail-fast caveat-removal tests-first increment on 2026-02-18:
- added failing migration tests in
  `tests/migration/test_naming_constants_consolidation.py` requiring
  `LocalRecord` and `KadiSyncManager` separator resolution to fail fast
  when config service is unavailable.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 25 passed, 292 deselected`.
- implementation status:
- removed remaining compatibility separator defaults from
  `src/ipat_watchdog/core/records/local_record.py` and
  `src/ipat_watchdog/core/sync/sync_kadi.py`.
- updated affected legacy unit tests to request `config_service` fixture in
  core records/storage/sync and SEM PhenomXL2 test modules.
- legacy verification:
  `python -m pytest -m legacy`
  returned `288 passed, 4 skipped, 27 deselected`.
- migration re-check:
  `python -m pytest -m migration`
  returned `27 passed, 292 deselected`.
- Phase 4 gate closed on 2026-02-18 after removing operational fallback usage
  from runtime config and naming reads.
- Phase 5 processing-pipeline decomposition kickoff on 2026-02-18:
- added decomposition report:
  `docs/reports/20260218-phase5-processing-pipeline-decomposition-report.md`
  mapping current `FileProcessManager` responsibilities into explicit
  stage boundaries (`resolve`, `stabilize`, `preprocess`, `route/rename`,
  `persist/sync`) with call-site coupling risks.
- added tests-first migration coverage in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring:
  explicit `_resolve_device_stage` and `_stabilize_artifact_stage` hooks and
  `process()` delegation through these hooks.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 27 passed, 292 deselected`.
- first implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract resolve/stabilize stage hooks and wire `process()` through them
  without changing external `ProcessingResult` behavior.
- green verification:
  `python -m pytest -m migration`
  returned `29 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 preprocess-stage tests-first increment on 2026-02-18:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `_preprocess_stage` and `_execute_pipeline` delegation through it.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 29 passed, 292 deselected`.
- second implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_preprocess_stage` and route `_execute_pipeline` through the
  preprocess seam without changing external processing outcomes.
- green verification:
  `python -m pytest -m migration`
  returned `31 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 persist/sync-stage tests-first increment on 2026-02-18:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `_persist_and_sync_stage` and ACCEPT-path delegation through it.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 31 passed, 292 deselected`.
- third implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_persist_and_sync_stage` and delegate ACCEPT routing side effects
  through this seam without changing processing outcomes.
- green verification:
  `python -m pytest -m migration`
  returned `33 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 route-decision-stage tests-first increment on 2026-02-18:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `_route_decision_stage` and ACCEPT reroute handling without
  redispatch through `_dispatch_route`.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 33 passed, 292 deselected`.
- fourth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_route_decision_stage` and route ACCEPT handling in
  `_route_with_prefix` through `_persist_and_sync_stage`.
- green verification:
  `python -m pytest -m migration`
  returned `35 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 non-ACCEPT-route-stage tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `_non_accept_route_stage` and non-ACCEPT reroute handling without
  redispatch through `_dispatch_route`.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 35 passed, 292 deselected`.
- fifth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_non_accept_route_stage` and route non-ACCEPT outcomes from
  `_dispatch_route` and `_route_with_prefix` through this seam.
- green verification:
  `python -m pytest -m migration`
  returned `37 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 rename-recursion-reduction tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  non-ACCEPT rename retries to avoid recursive `_route_with_prefix`
  re-entry.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 37 passed, 292 deselected`.
- sixth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  replace recursive rename retry control flow with an iterative
  `_invoke_rename_flow` loop while preserving existing ACCEPT, unappendable,
  and cancellation outcomes.
- green verification:
  `python -m pytest -m migration`
  returned `39 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 rename-retry-policy-stage tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `_rename_retry_policy_stage` and `_invoke_rename_flow`
  delegation of unappendable warning/context side effects through this seam.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 39 passed, 292 deselected`.
- seventh implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `_rename_retry_policy_stage` and use it from
  `_invoke_rename_flow` for non-ACCEPT retry policy decisions.
- green verification:
  `python -m pytest -m migration`
  returned `41 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 persist-candidate-record-stage tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `FileProcessManager._persist_candidate_record_stage` and
  `_persist_and_sync_stage` delegation through this seam.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 41 passed, 292 deselected`.
- eighth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `FileProcessManager._persist_candidate_record_stage` and route
  ACCEPT persistence from `_persist_and_sync_stage` through it.
- green verification:
  `python -m pytest -m migration`
  returned `43 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 post-persist-side-effects-stage tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `FileProcessManager._post_persist_side_effects_stage` and
  `add_item_to_record` delegation through this seam.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 43 passed, 292 deselected`.
- ninth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `FileProcessManager._post_persist_side_effects_stage` and route
  post-persist bookkeeping/metrics/immediate-sync side effects through it.
- green verification:
  `python -m pytest -m migration`
  returned `45 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 resolve-record-persistence-context-stage tests-first increment on
  2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `FileProcessManager._resolve_record_persistence_context_stage`
  and `add_item_to_record` delegation through this seam.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 45 passed, 292 deselected`.
- tenth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `FileProcessManager._resolve_record_persistence_context_stage` and
  route record/processor/path-id persistence context setup through this seam.
- green verification:
  `python -m pytest -m migration`
  returned `47 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 process-record-artifact-stage tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `FileProcessManager._process_record_artifact_stage` and
  `add_item_to_record` delegation through this seam.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 47 passed, 292 deselected`.
- eleventh implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `FileProcessManager._process_record_artifact_stage` and route
  processor invocation/output handling through this seam.
- green verification:
  `python -m pytest -m migration`
  returned `49 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 notify-success-retirement tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  `FileProcessManager.add_item_to_record` to drop the legacy `notify` flag
  and requiring `_persist_candidate_record_stage` to call it without a
  `notify` keyword argument.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 49 passed, 292 deselected`.
- twelfth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  remove legacy notify-success wiring from `add_item_to_record` and align
  ACCEPT persistence call sites to the simplified signature.
- updated migration and unit call sites still using `notify=False` to match
  the updated API contract.
- green verification:
  `python -m pytest -m migration`
  returned `51 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
- Phase 5 datatype-assignment-stage tests-first increment on 2026-02-19:
- added failing migration tests in
  `tests/migration/test_processing_pipeline_stage_boundaries.py` requiring
  explicit `FileProcessManager._assign_record_datatype_stage` and
  `add_item_to_record` delegation through this seam.
- red-state verification:
  `python -m pytest -m migration`
  returned `2 failed, 51 passed, 292 deselected`.
- thirteenth implementation increment status:
- updated `src/ipat_watchdog/core/processing/file_process_manager.py` to
  extract `FileProcessManager._assign_record_datatype_stage` and route
  datatype assignment through it from `add_item_to_record`.
- green verification:
  `python -m pytest -m migration`
  returned `53 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  returned `15 passed`.
