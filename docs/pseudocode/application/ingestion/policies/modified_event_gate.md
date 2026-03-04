---
id: application/ingestion/policies/modified_event_gate.py
origin_v1_files:
  - src/dpost/application/processing/modified_event_gate.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Debounce policy to suppress duplicate modified events.

## Origin Gist
- Source mapping: `src/dpost/application/processing/modified_event_gate.py`.
- Legacy gist: Debounces duplicate modified events.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Debounce policy to suppress duplicate modified events.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Candidate/event identity key (normalized path + fingerprint + event kind).
- Event timestamp and current clock reading.
- Debounce configuration (window duration, cache size, eviction policy).
- Prior gate state cache/store.

## Outputs
- Gate decision (`allow`, `defer`, `drop_duplicate`) with reason code.
- Updated gate state entry containing last-seen timestamp and counters.
- Next-eligible timestamp for deferred events.
- Optional diagnostics for observability.

## Invariants
- Decision function is deterministic for same key, timestamp, and prior state.
- Debounce window is non-negative and interpreted in one canonical time unit.
- Gate state updates are monotonic per key by timestamp.
- Reprocessing identical event id within window is idempotent and yields same decision class.

## Failure Modes
- Invalid debounce configuration yields `ModifiedEventGateConfigError`.
- Timestamp regression beyond tolerance yields `ModifiedEventGateTimeError`.
- State store access failure yields `ModifiedEventGateStateError`.
- Missing candidate/event key fields yields `ModifiedEventGateInputError`.

## Pseudocode
1. Build debounce key from candidate identity and normalized event kind.
2. Load prior gate state for key and validate timestamp monotonicity.
3. Compare current timestamp to last-seen timestamp and debounce window.
4. Return `drop_duplicate` or `defer` when inside window; otherwise return `allow`.
5. Persist updated state entry with new timestamp/counter information.
6. Emit optional diagnostics payload for tracing decisions.

## Tests To Implement
- unit: allow/defer/drop decisions across boundary timestamps, monotonic state updates, and invalid-config handling.
- integration: stabilize stage uses modified-event gate to suppress duplicate modified events without blocking distinct events.



