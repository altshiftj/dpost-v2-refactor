# Full Legacy Decoupling Functional + Architecture Audit

## Title
- Audit baseline for complete migration from `ipat_watchdog` runtime surfaces
  to `dpost` with strict functional equivalence and clean architecture.

## Date
- 2026-02-21

## Context
- Current Phase 9-13 progress has removed direct legacy imports from canonical
  startup modules and extracted several `dpost` boundaries.
- Full decoupling is not complete because core runtime behavior still depends
  on legacy config/processing/records/sync modules behind dpost infrastructure
  boundaries.
- A concrete audit baseline is required before final migration roadmap
  execution.

## Findings
- Startup entry surfaces are cleaner and now use native dpost bootstrap and
  infrastructure logging/observability modules.
- Runtime orchestration seams now exist in `dpost`, creating safe migration
  anchor points for deeper extraction.
- Runtime app loop ownership has been rehosted into
  `dpost.application.runtime.DeviceWatchdogApp`.
- Canonical runtime modules now use dpost-owned config/processing/session/
  storage imports without transition shim modules.
- Plugin discovery/loading and PC-device mapping are now dpost-owned boundary
  modules with canonical-only dpost hook/namespace loading paths.
- Record persistence and sync execution remain legacy-owned, including the
  primary Kadi implementation path.
- Current test posture is strong (`migration` and full suites green), which
  reduces risk for continued strangler extraction.

## Evidence
- Canonical runtime now uses native bootstrap and dpost infrastructure startup
  dependencies:
  - `src/dpost/runtime/bootstrap.py`
  - `src/dpost/infrastructure/runtime/bootstrap_dependencies.py`
  - `src/dpost/infrastructure/logging.py`
  - `src/dpost/infrastructure/observability.py`
- Runtime orchestration seams now available in `dpost`:
  - `src/dpost/runtime/composition.py`
  - `src/dpost/application/services/runtime_startup.py`
  - `src/dpost/application/runtime/device_watchdog_app.py`
  - `src/dpost/runtime/startup_config.py`
  - `src/dpost/plugins/profile_selection.py`
  - `src/dpost/plugins/loading.py`
  - `src/dpost/plugins/system.py`
  - `src/dpost/plugins/contracts.py`
  - `src/dpost/infrastructure/runtime/ui_factory.py`
  - `src/dpost/infrastructure/runtime/ui_adapters.py`
  - `src/dpost/infrastructure/runtime/desktop_ui.py`
  - `src/dpost/infrastructure/runtime/tkinter_ui.py`
  - `src/dpost/infrastructure/runtime/dialogs.py`
- Legacy runtime/application behavior still active:
  - `src/ipat_watchdog/core/processing/file_process_manager.py`
  - `src/ipat_watchdog/core/config/runtime.py`
  - `src/ipat_watchdog/core/records/record_manager.py`
  - `src/ipat_watchdog/core/sync/sync_kadi.py`
- Legacy plugin implementation packages still active:
  - `src/ipat_watchdog/device_plugins/`
  - `src/ipat_watchdog/pc_plugins/`

## Deprecated/Unsupported Behavior Rationale
- Legacy plugin namespace compatibility in canonical dpost paths is deprecated
  and retired.
  - Rationale: all in-repo plugins now have canonical dpost package ownership,
    so keeping dual namespace/hook fallback increases complexity with no parity
    benefit.
- Legacy runtime CLI startup (`python -m ipat_watchdog`) is deprecated for
  canonical operation.
  - Rationale: `dpost` is the single canonical runtime identity and composition
    root; split startup paths increase maintenance cost and contributor
    confusion.
- Transition-only request-preparation helper in dpost processing pipeline is
  deprecated and retired (`_ProcessingPipeline._prepare_request`).
  - Rationale: it was an unused stage-extraction bridge that obscured the final
    processing seam structure.

## Risks
- Rehosting runtime/bootstrap behavior can drift startup error semantics or
  service initialization ordering.
- Processing migration can cause hidden behavioral regressions across device
  plugins if stage boundaries are changed without parity checks.
- Plugin/config migration can break discovery/actionability if naming and
  dependency-group alignment is not preserved.
- Sync migration can alter side-effect timing and operator-visible failure
  messaging if immediate-sync semantics change.

## Open Questions
- Should full decoupling be performed as a one-shot rewrite?
  - Answer: No. Continue strict slice-by-slice strangler migration with
    migration tests red/green per boundary.
- Should runtime legacy adapters be deleted before feature parity evidence is
  complete?
  - Answer: No. Remove each adapter only after corresponding `dpost`
    implementation and parity tests are green.
- Should architecture cleanup be deferred until after legacy retirement?
  - Answer: No. Keep architecture cleanup in each migration slice to avoid
    accumulating technical debt in the new `dpost` surfaces.
