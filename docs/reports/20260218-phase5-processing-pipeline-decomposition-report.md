# Phase 5 Processing Pipeline Decomposition Report

## Date
- 2026-02-18

## Context
- Phase 4 is closed and green.
- Phase 5 starts with a decomposition map of `FileProcessManager` responsibilities into explicit pipeline stage boundaries before code extraction.

## Current End-to-End Call Path
1. `DeviceWatchdogApp._process_next_event()` calls `self.file_processing.process_item(src_path)` in `src/ipat_watchdog/core/app/device_watchdog_app.py:196`.
2. `FileProcessManager.process_item()` forwards to `_ProcessingPipeline.process()` in `src/ipat_watchdog/core/processing/file_process_manager.py:325` and `src/ipat_watchdog/core/processing/file_process_manager.py:63`.
3. `_ProcessingPipeline` now routes through explicit stage hooks `_resolve_device_stage()`, `_stabilize_artifact_stage()`, `_preprocess_stage()`, then `_execute_pipeline()` (`src/ipat_watchdog/core/processing/file_process_manager.py:65`, `src/ipat_watchdog/core/processing/file_process_manager.py:69`, `src/ipat_watchdog/core/processing/file_process_manager.py:126`, `src/ipat_watchdog/core/processing/file_process_manager.py:119`).

## Stage Boundary Map (Current Responsibilities)
| Target stage boundary | Current implementation ownership | Concrete call sites | Coupling notes |
|---|---|---|---|
| Resolve device | `_ProcessingPipeline._resolve_device_stage()` | `manager._device_resolver.resolve(path)` at `src/ipat_watchdog/core/processing/file_process_manager.py:90` | Resolution stage is coupled to internal staging-path filtering (`_is_internal_staging_path`) and immediate rejection side effects via `_reject_immediately()`. |
| Stabilize artifact | `_ProcessingPipeline._stabilize_artifact_stage()` | `FileStabilityTracker(request.source, request.device).wait()` at `src/ipat_watchdog/core/processing/file_process_manager.py:110` | Stability rejection path still carries rejection side effects (`_register_rejection`, `safe_move_to_exception`, `FILES_FAILED.inc`) in one stage method. |
| Preprocess | `_ProcessingPipeline._preprocess_stage()` + `_build_candidate()` + `_derive_candidate_metadata()` | `manager._resolve_processor(request.device)` at `src/ipat_watchdog/core/processing/file_process_manager.py:125`; stage delegation at `src/ipat_watchdog/core/processing/file_process_manager.py:126`; `processor.device_specific_preprocessing(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:147`; metadata parse at `src/ipat_watchdog/core/processing/file_process_manager.py:175` | Preprocess stage is coupled to config activation scope (`activate_device`) and filename parse/staging-suffix normalization details. |
| Route/rename decision | `_build_route_context()` + `_dispatch_route()` + `_invoke_rename_flow()` + `_route_with_prefix()` | `determine_routing_state(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:202` and `src/ipat_watchdog/core/processing/file_process_manager.py:263`; `handle_unappendable_record(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:219`; rename prompt via `obtain_valid_prefix(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:247` | Routing decisions are tightly coupled to UI rename interactions and recursive rerouting (`_route_with_prefix -> _dispatch_route`). |
| Persist/sync trigger | `_persist_and_sync_stage()` + `FileProcessManager.add_item_to_record()` | ACCEPT delegation at `src/ipat_watchdog/core/processing/file_process_manager.py:222`; stage method at `src/ipat_watchdog/core/processing/file_process_manager.py:227`; persistence call at `src/ipat_watchdog/core/processing/file_process_manager.py:231`; record persistence updates at `src/ipat_watchdog/core/processing/file_process_manager.py:380`; immediate sync trigger at `src/ipat_watchdog/core/processing/file_process_manager.py:402` | Persist stage seam is explicit, but underlying record mutation/metrics/sync side effects remain concentrated in `add_item_to_record()`. |

## Coupling Risks
1. Resolve and stabilize now have distinct methods, but both still embed reject/defer side effects; extracting side-effect policy from stage logic remains a follow-up risk (`src/ipat_watchdog/core/processing/file_process_manager.py:81` through `src/ipat_watchdog/core/processing/file_process_manager.py:117`).
2. Route logic now delegates ACCEPT to `_persist_and_sync_stage()`, reducing direct coupling, but route/rename flow still shares one orchestrator and recursive control path (`src/ipat_watchdog/core/processing/file_process_manager.py:211` through `src/ipat_watchdog/core/processing/file_process_manager.py:277`).
3. Rename flow recursively re-enters dispatch (`_route_with_prefix -> _dispatch_route`), which complicates isolated stage testing and makes control flow harder to reason about (`src/ipat_watchdog/core/processing/file_process_manager.py:258` through `src/ipat_watchdog/core/processing/file_process_manager.py:271`).
4. `add_item_to_record()` combines plugin processing, record mutation, force-path expansion, metrics, and immediate sync in one hotspot (`src/ipat_watchdog/core/processing/file_process_manager.py:341` through `src/ipat_watchdog/core/processing/file_process_manager.py:403`).
5. Error handling spans across stage boundaries in `_execute_pipeline()` and `_handle_processing_failure()`, so extraction must preserve current exception-routing semantics for both effective and preprocessed paths (`src/ipat_watchdog/core/processing/file_process_manager.py:133` through `src/ipat_watchdog/core/processing/file_process_manager.py:136`, `src/ipat_watchdog/core/processing/file_process_manager.py:440` through `src/ipat_watchdog/core/processing/file_process_manager.py:455`).

## Extraction Order Recommendation (Incremental)
1. Split resolve-device and stabilize-artifact into separate stage hooks while preserving existing return models (`ProcessingRequest` / `ProcessingResult`).
2. Extract preprocess stage boundary without changing candidate metadata semantics.
3. Separate route/rename decision stage from persist/sync stage so ACCEPT path no longer persists inside route decision code.
4. Keep existing integration behavior stable by retaining `FileProcessManager.process_item()` and `ProcessingResult` contract unchanged.

## Update Addendum (2026-02-18)
- Completed extraction increment 1:
  `_resolve_device_stage()` and `_stabilize_artifact_stage()` were extracted
  and wired in `process()`.
- Completed extraction increment 2:
  `_preprocess_stage()` was extracted and wired in `_execute_pipeline()`.
- Completed extraction increment 3:
  `_persist_and_sync_stage()` was extracted and wired from
  `_dispatch_route()` for ACCEPT decisions.
- Verification after increment 2:
  `python -m pytest -m migration`
  -> `33 passed, 292 deselected`.
  `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
  -> `15 passed`.
