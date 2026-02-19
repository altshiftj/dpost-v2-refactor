# Phase 5 Processing Pipeline Decomposition Report

## Date
- 2026-02-18

## Context
- Phase 4 is closed and green.
- Phase 5 starts with a decomposition map of `FileProcessManager` responsibilities into explicit pipeline stage boundaries before code extraction.

## Current End-to-End Call Path
1. `DeviceWatchdogApp._process_next_event()` calls `self.file_processing.process_item(src_path)` in `src/ipat_watchdog/core/app/device_watchdog_app.py:196`.
2. `FileProcessManager.process_item()` forwards to `_ProcessingPipeline.process()` in `src/ipat_watchdog/core/processing/file_process_manager.py:331` and `src/ipat_watchdog/core/processing/file_process_manager.py:63`.
3. `_ProcessingPipeline` now routes through explicit stage hooks `_resolve_device_stage()`, `_stabilize_artifact_stage()`, `_preprocess_stage()`, then `_execute_pipeline()` (`src/ipat_watchdog/core/processing/file_process_manager.py:65`, `src/ipat_watchdog/core/processing/file_process_manager.py:69`, `src/ipat_watchdog/core/processing/file_process_manager.py:126`, `src/ipat_watchdog/core/processing/file_process_manager.py:119`).

## Stage Boundary Map (Current Responsibilities)
| Target stage boundary | Current implementation ownership | Concrete call sites | Coupling notes |
|---|---|---|---|
| Resolve device | `_ProcessingPipeline._resolve_device_stage()` | `manager._device_resolver.resolve(path)` at `src/ipat_watchdog/core/processing/file_process_manager.py:90` | Resolution stage is coupled to internal staging-path filtering (`_is_internal_staging_path`) and immediate rejection side effects via `_reject_immediately()`. |
| Stabilize artifact | `_ProcessingPipeline._stabilize_artifact_stage()` | `FileStabilityTracker(request.source, request.device).wait()` at `src/ipat_watchdog/core/processing/file_process_manager.py:110` | Stability rejection path still carries rejection side effects (`_register_rejection`, `safe_move_to_exception`, `FILES_FAILED.inc`) in one stage method. |
| Preprocess | `_ProcessingPipeline._preprocess_stage()` + `_build_candidate()` + `_derive_candidate_metadata()` | `manager._resolve_processor(request.device)` at `src/ipat_watchdog/core/processing/file_process_manager.py:125`; stage delegation at `src/ipat_watchdog/core/processing/file_process_manager.py:126`; `processor.device_specific_preprocessing(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:147`; metadata parse at `src/ipat_watchdog/core/processing/file_process_manager.py:175` | Preprocess stage is coupled to config activation scope (`activate_device`) and filename parse/staging-suffix normalization details. |
| Route/rename decision | `_route_decision_stage()` + `_dispatch_route()` + `_non_accept_route_stage()` + `_invoke_rename_flow()` + `_rename_retry_policy_stage()` + `_route_with_prefix()` | decision stage at `src/ipat_watchdog/core/processing/file_process_manager.py`; `determine_routing_state(...)` in routing helpers; non-ACCEPT seam in `_non_accept_route_stage()`; `handle_unappendable_record(...)` in `record_flow`; rename prompt via `obtain_valid_prefix(...)`; retry policy via `_rename_retry_policy_stage()` | Route decision and non-ACCEPT seams are explicit; rename retries evaluate iteratively inside `_invoke_rename_flow()` and delegate retry warning/context policy through `_rename_retry_policy_stage()`. |
| Persist/sync trigger | `_persist_and_sync_stage()` + `FileProcessManager._persist_candidate_record_stage()` + `FileProcessManager.add_item_to_record()` + `FileProcessManager._resolve_record_persistence_context_stage()` + `FileProcessManager._process_record_artifact_stage()` + `FileProcessManager._assign_record_datatype_stage()` + `FileProcessManager._finalize_record_output_stage()` + `FileProcessManager._post_persist_side_effects_stage()` | ACCEPT delegation in `_persist_and_sync_stage()`; manager persistence seam in `_persist_candidate_record_stage()`; context seam in `_resolve_record_persistence_context_stage()`; processor seam in `_process_record_artifact_stage()`; datatype seam in `_assign_record_datatype_stage()`; finalization seam in `_finalize_record_output_stage()`; post-persist bookkeeping/metrics/sync seam in `_post_persist_side_effects_stage()` | Persist stage seam is explicit and now delegates through manager seams for persistence, record context resolution, processor invocation/output handling, datatype assignment, output finalization, and post-persist side effects; remaining coupling is centered on stage-call ordering in `add_item_to_record()`. |

## Coupling Risks
1. Resolve and stabilize now have distinct methods, but both still embed reject/defer side effects; extracting side-effect policy from stage logic remains a follow-up risk (`src/ipat_watchdog/core/processing/file_process_manager.py:81` through `src/ipat_watchdog/core/processing/file_process_manager.py:117`).
2. Route decision and non-ACCEPT handling now have explicit seams and rename retries no longer recurse through `_route_with_prefix()`. Retry warning/context policy is extracted to `_rename_retry_policy_stage()`, but prompt loops still live in one orchestration class (`src/ipat_watchdog/core/processing/file_process_manager.py`).
3. `add_item_to_record()` now delegates record-context setup, processor invocation/output handling, datatype assignment, output finalization, and post-persist side effects; remaining hotspot is stage-call ordering (`src/ipat_watchdog/core/processing/file_process_manager.py`).
4. Error handling spans across stage boundaries in `_execute_pipeline()` and `_handle_processing_failure()`, so extraction must preserve current exception-routing semantics for both effective and preprocessed paths (`src/ipat_watchdog/core/processing/file_process_manager.py:133` through `src/ipat_watchdog/core/processing/file_process_manager.py:136`, `src/ipat_watchdog/core/processing/file_process_manager.py:446` through `src/ipat_watchdog/core/processing/file_process_manager.py:461`).

## Extraction Order Recommendation (Incremental)
1. Split resolve-device and stabilize-artifact into separate stage hooks while preserving existing return models (`ProcessingRequest` / `ProcessingResult`).
2. Extract preprocess stage boundary without changing candidate metadata semantics.
3. Separate route/rename decision stage from persist/sync stage so ACCEPT path no longer persists inside route decision code.
4. Keep existing integration behavior stable by retaining `FileProcessManager.process_item()` and `ProcessingResult` contract unchanged.

## Update Addendum (2026-02-18 to 2026-02-19)
- Completed extraction increment 1:
  `_resolve_device_stage()` and `_stabilize_artifact_stage()` were extracted
  and wired in `process()`.
- Completed extraction increment 2:
  `_preprocess_stage()` was extracted and wired in `_execute_pipeline()`.
- Completed extraction increment 3:
  `_persist_and_sync_stage()` was extracted and wired from
  `_dispatch_route()` for ACCEPT decisions.
- Completed extraction increment 4:
  `_route_decision_stage()` was extracted and `_route_with_prefix()` now
  routes ACCEPT directly through `_persist_and_sync_stage()`.
- Completed extraction increment 5:
  `_non_accept_route_stage()` was extracted and non-ACCEPT outcomes from
  `_dispatch_route()` and `_route_with_prefix()` now delegate through it.
- Verification after increment 5:
  `python -m pytest -m migration`
  -> `37 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 6:
  `_invoke_rename_flow()` now evaluates rename retries iteratively, removing
  recursive `_route_with_prefix()` re-entry from non-ACCEPT rename paths.
- Verification after increment 6:
  `python -m pytest -m migration`
  -> `39 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 7:
  `_rename_retry_policy_stage()` was extracted and `_invoke_rename_flow()`
  now delegates unappendable warning/context retry policy through this seam.
- Verification after increment 7:
  `python -m pytest -m migration`
  -> `41 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 8:
  `_persist_candidate_record_stage()` was extracted on
  `FileProcessManager`, and `_persist_and_sync_stage()` now delegates ACCEPT
  persistence through this manager seam.
- Verification after increment 8:
  `python -m pytest -m migration`
  -> `43 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 9:
  `_post_persist_side_effects_stage()` was extracted on
  `FileProcessManager`, and `add_item_to_record()` now delegates
  bookkeeping/metrics/immediate-sync side effects through this seam.
- Verification after increment 9:
  `python -m pytest -m migration`
  -> `45 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 10:
  `_resolve_record_persistence_context_stage()` was extracted on
  `FileProcessManager`, and `add_item_to_record()` now delegates
  record/processor/path-id setup through this seam.
- Verification after increment 10:
  `python -m pytest -m migration`
  -> `47 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 11:
  `_process_record_artifact_stage()` was extracted on `FileProcessManager`,
  and `add_item_to_record()` now delegates processor invocation/output
  handling through this seam.
- Verification after increment 11:
  `python -m pytest -m migration`
  -> `49 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 12:
  legacy notify-success wiring was retired from
  `FileProcessManager.add_item_to_record()`, removing the `notify` argument
  and corresponding success-notification side effect path.
- Verification after increment 12:
  `python -m pytest -m migration`
  -> `51 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 13:
  `_assign_record_datatype_stage()` was extracted on
  `FileProcessManager`, and `add_item_to_record()` now delegates datatype
  assignment through this seam.
- Verification after increment 13:
  `python -m pytest -m migration`
  -> `53 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
- Completed extraction increment 14:
  `_finalize_record_output_stage()` was extracted on
  `FileProcessManager`, and `add_item_to_record()` now delegates output
  finalization through this seam.
- Verification after increment 14:
  `python -m pytest -m migration`
  -> `55 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
