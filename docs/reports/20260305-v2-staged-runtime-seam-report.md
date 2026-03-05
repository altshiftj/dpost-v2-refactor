# Report: V2 Staged Runtime Seam

## Scope
- Worktree:
  - `.worktrees/laneD-closeout`
- Goal:
  - close the shared deferred/staged runtime seam for `psa_horiba` and `utm_zwick`
  - preserve existing SEM runtime behavior
  - make closeout green without reintroducing legacy fallback paths

## Why this slice mattered
- Plugin-local parity was already green for:
  - `sem_phenomxl2`
  - `utm_zwick`
  - `psa_horiba`
- The remaining blocker sat in shared runtime behavior:
  - staged pre-events were treated as reject/fail outcomes
  - runtime processor instances were rebuilt per event, so staged plugins lost in-memory state
  - persist still moved the raw source path instead of finalized processor outputs

## Shared seam changes
- Transform stage:
  - `can_process == False` now yields `PipelineTerminalOutcome.RETRY`
  - diagnostics now record `reason_code="deferred"`
- Transition table:
  - `transform` now allows terminal `RETRY`
- Runtime processor selection:
  - selection uses declared source-extension support before immediate readiness
  - processor instances are cached per plugin for the runtime session so staged state survives across events
- Headless event discovery:
  - watch-dir events are ordered by file `mtime_ns`, then path
  - this keeps one-pass staged sequences deterministic
- Persist stage:
  - moves `processor_result.final_path` plus normalized `force_paths`
  - deduplicates duplicate final artifacts
  - persists normalized processed-path payloads instead of raw pre-move paths
- Device restriction policy:
  - `plugins.device_plugins` now narrows runtime selection even without a selected PC plugin

## Tests added or updated first
- `tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py`
  - transform not-ready -> deferred retry
- `tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`
  - finalized artifact move plan and normalized persisted paths
- `tests/dpost_v2/application/ingestion/test_pipeline_integration.py`
  - transform retry maps to `IngestionOutcomeKind.DEFERRED_RETRY`
- `tests/dpost_v2/runtime/test_composition.py`
  - headless event ordering by mtime
  - staged Zwick runtime path
  - staged PSA runtime path
  - mixed target-device one-pass headless proof
  - persisted processor-result path normalization

## Validation
- `python -m pytest -q tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py tests/dpost_v2/application/ingestion/test_pipeline_integration.py tests/dpost_v2/runtime/test_composition.py`
  - `43 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pytest -q tests/dpost_v2`
  - `426 passed`

## Result
- `tischrem_blb -> sem_phenomxl2` still succeeds end-to-end
- `zwick_blb -> utm_zwick` now defers the raw `.zs2` pre-event and finalizes on matching `.xlsx`
- `horiba_blb -> psa_horiba` now defers staged pre-events and finalizes the sentinel batch in one watch-loop pass
- restricted headless target-device runs can process SEM + Zwick + PSA in one pass with:
  - `processed_count = 7`
  - `failed_count = 0`
  - `terminal_reason = end_of_stream`
  - `3` persisted records

## Deferred but still accepted
- `utm_zwick`
  - TTL/session-end flush
  - overwrite/unique-move hardening beyond current parity slice
- `psa_horiba`
  - rename-cancel whole-folder handling
  - exception-bucket behavior
- runtime
  - successful sync metadata is still not normalized back into record payload beyond current `sync_status` path
