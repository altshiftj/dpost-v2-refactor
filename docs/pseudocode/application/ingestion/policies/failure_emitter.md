---
id: application/ingestion/policies/failure_emitter.py
origin_v1_files:
  - src/dpost/application/processing/failure_emitter.py
lane: Processing-Kernel
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Failure event emission adapter hooks.

## Origin Gist
- Source mapping: `src/dpost/application/processing/failure_emitter.py`.
- Legacy gist: Emits standardized failure events and logs.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Failure event emission adapter hooks.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Canonical `FailureOutcome` model.
- Processing/runtime context for correlation fields.
- Event and logging ports from runtime services.
- Emission policy settings (rate limits, redaction rules, escalation thresholds).

## Outputs
- Emission result model (`emitted`, `suppressed`, `emit_failed`).
- Structured event payload passed to event/logging ports.
- Emission diagnostics including suppression reason or adapter failure reason.
- Optional escalation signal for severe/terminal failures.

## Invariants
- Emitter never mutates incoming `FailureOutcome`.
- Event payload schema is stable and JSON-serializable.
- Suppression decisions are deterministic for identical outcome + policy inputs.
- Emission failures are reported as typed results, not swallowed silently.

## Failure Modes
- Event port unavailable yields `FailureEmissionPortError`.
- Payload serialization failure yields `FailureEmissionSerializationError`.
- Policy misconfiguration yields `FailureEmissionPolicyError`.
- Logging/event adapter timeout yields `FailureEmissionTimeoutError`.

## Pseudocode
1. Build normalized failure event payload from `FailureOutcome` + correlation context.
2. Apply suppression/rate-limit policy before dispatch.
3. If emission is allowed, send payload to event port and structured logger.
4. Capture adapter response statuses and map any adapter errors to typed emission errors.
5. Return `EmissionResult` with emitted/suppressed/failed terminal type.
6. Raise escalation signal flag when severity/policy threshold is reached.

## Tests To Implement
- unit: payload formatting, suppression policy decisions, and adapter error mapping.
- integration: engine failure outcomes are emitted once with stable payload shape and escalation flags across retries/terminal failures.



