---
id: domain/processing/staging.py
origin_v1_files:
  - src/dpost/domain/processing/staging.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Staging-domain invariants and transitions.

## Origin Gist
- Source mapping: `src/dpost/domain/processing/staging.py`.
- Legacy gist: Retains processing domain model or policy staging.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Staging-domain invariants and transitions.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Current staging state token.
- Staging event trigger (`observed`, `stabilized`, `routed`, `persisted`, `failed`, `rejected`).
- Optional transition metadata (reason code, attempt index).
- Transition policy table.

## Outputs
- Next staging state token and transition reason.
- Transition validation result for illegal state/event pairs.
- Helper predicates for terminal/non-terminal staging states.
- Canonical state transition trace entry model.

## Invariants
- State machine permits transitions only from defined source states.
- Terminal states (`persisted`, `failed`, `rejected`) have no outgoing transitions.
- Transition metadata includes reason code for non-happy paths.
- Example: `stabilized` + `routed` event transitions to `routed` state.
- Counterexample: `persisted` transitioning back to `resolving` is invalid.

## Failure Modes
- Undefined source state raises `StagingStateUnknownError`.
- Illegal transition pair raises `StagingTransitionError`.
- Missing required reason for failure/reject transition raises `StagingReasonRequiredError`.
- Attempt index regression in transition metadata raises `StagingAttemptOrderError`.

## Pseudocode
1. Define finite state set and transition table mapping `(state, event)` to next state.
2. Validate incoming current state and event trigger against transition table.
3. If transition exists, build next-state result with normalized reason metadata.
4. Enforce terminal-state rules (no outbound transitions from terminal states).
5. Emit canonical transition trace entry for consumers.
6. Return typed error for invalid state/event combinations.

## Tests To Implement
- unit: valid transition paths, terminal-state lock behavior, and invalid transition rejection.
- integration: ingestion pipeline state transitions map cleanly to staging domain states across success, retry, reject, and failure paths.



