---
id: application/ingestion/stages/stabilize.py
origin_v1_files:
  - src/dpost/application/processing/stability_timing_policy.py
  - src/dpost/application/processing/stability_tracker.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Stability gate logic and settle-time policy application.

## Origin Gist
- Source mapping: `src/dpost/application/processing/stability_timing_policy.py`, `src/dpost/application/processing/stability_tracker.py`.
- Legacy gist: Keeps stabilization timing policy near stabilize stage. Implements stability guard stage logic.

## V2 Improvement Intent
- Transform posture: Merge.
- Target responsibility: Stability gate logic and settle-time policy application.
- Improvement goal: Consolidate duplicated logic into a single canonical owner.
## Inputs
- Resolved candidate metadata from resolve stage.
- Stability settings (settle delay, debounce window, max wait, ignore patterns).
- Modified-event gate policy and clock readings.
- Optional prior event state cache keyed by candidate identity/path.

## Outputs
- `StabilizeStageResult` with terminal type `ready`, `defer_retry`, or `drop_duplicate`.
- Updated stabilization state snapshot for future events.
- Retry plan hint for deferred outcomes.
- Stage diagnostics (elapsed settle time, debounce decision reason).

## Invariants
- Candidate is forwarded only when stability policy marks it ready.
- Debounce key calculation is deterministic and based on candidate identity/path.
- Stabilize stage does not perform file persistence or routing decisions.
- Terminal result type is explicit and limited to stabilize contract values.

## Failure Modes
- Invalid/negative settle settings yield `StabilizePolicyConfigurationError`.
- Clock regression during stabilization yields `StabilizeTimeSourceError`.
- Gate state backend failure yields typed failure outcome (retryable by policy).
- Missing required candidate timestamps yields `StabilizeCandidateError`.

## Pseudocode
1. Compute debounce/stabilization key from candidate identity and source path.
2. Consult modified-event gate with current timestamp and configured debounce window.
3. If gate says duplicate within window, return `drop_duplicate` terminal result.
4. Evaluate settle-time policy using file timestamps and configured thresholds.
5. Return `defer_retry` with retry hint when still unstable, else return `ready` with unchanged candidate.
6. Persist updated gate/stability state for subsequent events.

## Tests To Implement
- unit: duplicate suppression, settle-time evaluation, defer-ready transitions, and clock regression handling.
- integration: pipeline stabilize stage defers unstable files and later forwards the same candidate when stabilization criteria are met.



