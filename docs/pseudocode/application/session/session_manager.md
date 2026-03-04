---
id: application/session/session_manager.py
origin_v1_files:
  - src/dpost/application/session/session_manager.py
lane: Runtime-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Session timeout, state transitions, and lifecycle hooks.

## Origin Gist
- Source mapping: `src/dpost/application/session/session_manager.py`.
- Legacy gist: Retains session management module session_manager.py in runtime layer.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Session timeout, state transitions, and lifecycle hooks.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Session policy settings (idle timeout, max runtime, heartbeat interval).
- Clock port for deterministic time evaluation.
- Session lifecycle events (`start`, `activity`, `pause`, `resume`, `stop`, `abort`).
- Optional callback hooks for UI/observability notifications.

## Outputs
- `SessionState` value object (`inactive`, `starting`, `active`, `stopping`, `aborted`, `completed`).
- Transition result model with previous state, next state, and reason code.
- Expiration decisions (`still_active`, `soft_timeout`, `hard_timeout`).
- Session summary snapshot for runtime shutdown diagnostics.

## Invariants
- State transitions follow explicit transition table; invalid jumps are rejected.
- Session ids are unique per runtime and immutable after creation.
- Re-applying `start` to an already active identical session id is idempotent (no duplicate side effects).
- Timeout checks are monotonic with respect to clock readings.

## Failure Modes
- Invalid transition request raises `SessionTransitionError`.
- Missing session before activity/stop call raises `SessionNotStartedError`.
- Clock regression detected during timeout checks raises `SessionTimeSourceError`.
- Callback hook failure is isolated and returned as structured warning/failure outcome.

## Pseudocode
1. Define explicit transition matrix and immutable `SessionState` model with timestamps.
2. Implement `start_session(context)` that creates active state or returns idempotent existing state.
3. Implement `record_activity(session_id, event_time)` to update heartbeat and evaluate timeout policy.
4. Implement `stop_session` and `abort_session` with deterministic terminal state mapping.
5. Implement `evaluate_timeouts(now)` to classify soft/hard timeout outcomes for runtime loop decisions.
6. Emit transition callbacks/events without allowing callback failures to corrupt state machine integrity.

## Tests To Implement
- unit: transition table enforcement, idempotent `start_session`, timeout evaluation, and clock regression handling.
- integration: runtime loop interacts with session manager across normal completion, idle timeout, and abort scenarios.



