# Phase 5 Processing Pipeline Decomposition Report

## Date
- 2026-02-18

## Context
- Phase 4 is closed and green.
- Phase 5 starts with a decomposition map of `FileProcessManager` responsibilities into explicit pipeline stage boundaries before code extraction.

## Current End-to-End Call Path
1. `DeviceWatchdogApp._process_next_event()` calls `self.file_processing.process_item(src_path)` in `src/ipat_watchdog/core/app/device_watchdog_app.py:196`.
2. `FileProcessManager.process_item()` forwards to `_ProcessingPipeline.process()` in `src/ipat_watchdog/core/processing/file_process_manager.py:301` and `src/ipat_watchdog/core/processing/file_process_manager.py:63`.
3. `_ProcessingPipeline` currently routes through `_prepare_request()` and `_execute_pipeline()` (`src/ipat_watchdog/core/processing/file_process_manager.py:65` and `src/ipat_watchdog/core/processing/file_process_manager.py:68`).

## Stage Boundary Map (Current Responsibilities)
| Target stage boundary | Current implementation ownership | Concrete call sites | Coupling notes |
|---|---|---|---|
| Resolve device | `_ProcessingPipeline._prepare_request()` | `manager._device_resolver.resolve(path)` at `src/ipat_watchdog/core/processing/file_process_manager.py:79` | Resolution stage is coupled to internal staging-path filtering (`_is_internal_staging_path`) and immediate rejection side effects via `_reject_immediately()`. |
| Stabilize artifact | `_ProcessingPipeline._prepare_request()` | `FileStabilityTracker(path, device).wait()` at `src/ipat_watchdog/core/processing/file_process_manager.py:93` | Stability rejection path is coupled to failure side effects (`_register_rejection`, `safe_move_to_exception`, `FILES_FAILED.inc`) in the same method as device resolution. |
| Preprocess | `_ProcessingPipeline._execute_pipeline()` + `_build_candidate()` + `_derive_candidate_metadata()` | `manager._resolve_processor(request.device)` at `src/ipat_watchdog/core/processing/file_process_manager.py:109`; `processor.device_specific_preprocessing(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:123`; metadata parse at `src/ipat_watchdog/core/processing/file_process_manager.py:152` | Preprocess stage is coupled to config activation scope (`activate_device`) and filename parse/staging-suffix normalization details. |
| Route/rename decision | `_build_route_context()` + `_dispatch_route()` + `_invoke_rename_flow()` + `_route_with_prefix()` | `determine_routing_state(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:178` and `src/ipat_watchdog/core/processing/file_process_manager.py:239`; `handle_unappendable_record(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:195`; rename prompt via `obtain_valid_prefix(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:223` | Routing decisions are tightly coupled to UI rename interactions and recursive rerouting (`_route_with_prefix -> _dispatch_route`). |
| Persist/sync trigger | `_dispatch_route()` ACCEPT branch + `FileProcessManager.add_item_to_record()` | `manager.add_item_to_record(...)` at `src/ipat_watchdog/core/processing/file_process_manager.py:198`; record persistence updates at `src/ipat_watchdog/core/processing/file_process_manager.py:350`; immediate sync trigger at `src/ipat_watchdog/core/processing/file_process_manager.py:372` | Persist stage mixes record creation/update, filesystem/path generation, plugin processing output handling, metrics, and optional sync trigger in one method. |

## Coupling Risks
1. Resolve and stabilize are co-located in `_prepare_request()`, so edits to resolution policy can unintentionally change stability rejection behavior (`src/ipat_watchdog/core/processing/file_process_manager.py:70` through `src/ipat_watchdog/core/processing/file_process_manager.py:101`).
2. Route logic directly performs persistence on ACCEPT in `_dispatch_route()`, which blurs decision vs side-effect boundaries and increases regression blast radius (`src/ipat_watchdog/core/processing/file_process_manager.py:197` through `src/ipat_watchdog/core/processing/file_process_manager.py:210`).
3. Rename flow recursively re-enters dispatch (`_route_with_prefix -> _dispatch_route`), which complicates isolated stage testing and makes control flow harder to reason about (`src/ipat_watchdog/core/processing/file_process_manager.py:234` through `src/ipat_watchdog/core/processing/file_process_manager.py:247`).
4. `add_item_to_record()` combines plugin processing, record mutation, force-path expansion, metrics, and immediate sync in one hotspot (`src/ipat_watchdog/core/processing/file_process_manager.py:317` through `src/ipat_watchdog/core/processing/file_process_manager.py:379`).
5. Error handling spans across stage boundaries in `_execute_pipeline()` and `_handle_processing_failure()`, so extraction must preserve current exception-routing semantics for both effective and preprocessed paths (`src/ipat_watchdog/core/processing/file_process_manager.py:116` through `src/ipat_watchdog/core/processing/file_process_manager.py:120`, `src/ipat_watchdog/core/processing/file_process_manager.py:416` through `src/ipat_watchdog/core/processing/file_process_manager.py:431`).

## Extraction Order Recommendation (Incremental)
1. Split resolve-device and stabilize-artifact into separate stage hooks while preserving existing return models (`ProcessingRequest` / `ProcessingResult`).
2. Extract preprocess stage boundary without changing candidate metadata semantics.
3. Separate route/rename decision stage from persist/sync stage so ACCEPT path no longer persists inside route decision code.
4. Keep existing integration behavior stable by retaining `FileProcessManager.process_item()` and `ProcessingResult` contract unchanged.
