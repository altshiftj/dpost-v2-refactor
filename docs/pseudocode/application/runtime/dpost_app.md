---
id: application/runtime/dpost_app.py
origin_v1_files:
  - src/dpost/application/runtime/device_watchdog_app.py
lane: Runtime-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Top-level orchestration loop for observer events -> ingestion engine -> outcomes.

## Origin Gist
- Source mapping: `src/dpost/application/runtime/device_watchdog_app.py`.
- Legacy gist: Keeps top-level dpost app orchestration with explicit collaborators.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Top-level orchestration loop for observer events -> ingestion engine -> outcomes.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Runtime lifecycle controls (`start`, `stop`, cancellation token, graceful shutdown timeout).
- Event source stream (filesystem observer or equivalent ingress adapter output).
- Core collaborators: `SessionManager`, ingestion `Engine`, `RecordsService`, and event/UI ports.
- `RuntimeContext` seed used to derive per-event processing context.

## Outputs
- `RunResult` summary with processed/skipped/failed counters and terminal reason.
- Emitted application events for each stage outcome and lifecycle transition.
- Session lifecycle transitions coordinated with runtime progress.
- Graceful shutdown completion status and teardown diagnostics.

## Invariants
- App orchestration stays in application layer and invokes side effects through ports only.
- Observer events are processed in arrival order within a single runtime loop.
- Replaying the same observer event id is idempotent at app boundary (duplicate side effects are prevented by downstream gate/persist contracts).
- Runtime always emits a terminal lifecycle event when loop exits.

## Failure Modes
- Event source failure yields normalized runtime failure outcome and controlled shutdown.
- Ingestion engine terminal error yields failure event and stops loop based on policy.
- Port cancellation/timeouts yield recoverable or terminal outcomes per policy settings.
- Unhandled exception in orchestrator yields emergency shutdown path with failure emission.

## Pseudocode
1. Initialize runtime session through `SessionManager` and emit `runtime_started` event.
2. Enter main loop: read next observer event, derive `ProcessingContext`, and call ingestion engine.
3. Route ingestion result to event/UI/reporting sinks and update counters/state.
4. Apply retry/continue/abort decision policy for recoverable failures.
5. Exit loop on cancellation, terminal failure, or clean end-of-stream and emit terminal event.
6. Execute teardown hooks and return deterministic `RunResult`.

## Tests To Implement
- unit: loop control around cancellation/terminal failure, event ordering guarantees, and duplicate-event idempotency behavior.
- integration: runtime app wired through composition processes observer events end-to-end and emits terminal lifecycle events on both success and failure shutdown paths.



