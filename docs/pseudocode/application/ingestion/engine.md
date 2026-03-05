---
id: application/ingestion/engine.py
origin_v1_files:
  - src/dpost/application/processing/file_process_manager.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Stage runner coordinating resolve/stabilize/route/persist/post-persist stages.

## Origin Gist
- Source mapping: `src/dpost/application/processing/file_process_manager.py`.
- Legacy gist: Replaces orchestration shell with explicit ingestion engine.

## V2 Improvement Intent
- Transform posture: Split.
- Target responsibility: Stage runner coordinating resolve/stabilize/route/persist/post-persist stages.
- Improvement goal: Decompose orchestration into focused modules/stages with tighter ownership.
## Inputs
- Incoming file-system event payload and seed `ProcessingContext`.
- Stage pipeline runner (`pipeline`) and stage handlers (`resolve`, `stabilize`, `route`, `persist`, `post_persist`).
- Runtime services facade for side effects.
- Failure handling policies (`error_handling`, `failure_outcome`, `failure_emitter`, `retry_planner`).

## Outputs
- Terminal `IngestionOutcome` (`succeeded`, `deferred_stage`, `deferred_retry`, `rejected`, `failed_terminal`).
- Stage execution trace for observability and debugging.
- Optional retry plan attached to retryable failure outcomes.
- Emitted failure events when terminal or escalation policy requires them.

## Invariants
- Stage order is fixed: resolve -> stabilize -> route -> persist -> post-persist.
- Exactly one terminal outcome is returned per input event.
- Stage input snapshots are immutable; each stage returns a new state object.
- Unhandled exceptions are normalized into failure outcomes before returning.

## Failure Modes
- Stage contract violation yields `IngestionStageContractError` and terminal failure outcome.
- Unexpected stage exception is mapped by `error_handling` policy and may become retryable.
- Cancellation request mid-run returns deterministic aborted/failed terminal outcome.
- Missing required stage handler binding yields startup-time `IngestionEngineConfigurationError`.

## Pseudocode
1. Create initial pipeline state from observer event and `ProcessingContext`.
2. Execute stage graph via `pipeline.run(initial_state, stage_handlers)`.
3. For each stage transition, append trace entries with stage id, status, and correlation id.
4. On raised exception, convert exception to normalized failure outcome via `error_handling` and `failure_outcome`.
5. If outcome requires emission, call `failure_emitter` and attach emission status.
6. Return terminal `IngestionOutcome` with optional retry plan and stage trace.

## Tests To Implement
- unit: fixed stage ordering, single terminal outcome guarantee, and exception normalization to retry/terminal outcomes.
- integration: runtime app calls engine for real observer events and receives deterministic outcomes plus failure emissions across all stage paths.



