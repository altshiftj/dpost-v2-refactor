---
id: application/contracts/events.py
origin_v1_files:
  - src/dpost/application/interactions/messages.py
lane: Contracts-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Event/message dataclasses and enums shared across lanes.

## Origin Gist
- Source mapping: `src/dpost/application/interactions/messages.py`.
- Legacy gist: Normalizes interaction messages as shared application events.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Event/message dataclasses and enums shared across lanes.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Runtime and ingestion lifecycle transitions that need cross-lane signaling.
- Domain outcomes from routing/persist policies and failure normalization policies.
- UI/sync observability needs that require stable event payload contracts.
- Correlation metadata supplied by `RuntimeContext`/`ProcessingContext`.

## Outputs
- Stable enums for event kind, severity, and source stage.
- Dataclasses for success, warning, and failure event payloads with shared base fields.
- Event serialization contract used by UI adapters, logs, and optional event sinks.
- Factory helpers that convert stage outcomes into canonical event instances.

## Invariants
- Every event contains `event_id`, `trace_id`, `occurred_at`, and `stage`.
- Event kinds are append-only to preserve compatibility for adapters and tests.
- Payload dictionaries are JSON-serializable primitives or nested contract models only.
- Failure events include normalized severity and machine-readable reason codes.

## Failure Modes
- Creating an event with unknown kind/stage raises `EventContractError`.
- Missing correlation fields raises `EventValidationError`.
- Non-serializable payload values raise `EventSerializationError`.
- Factory conversion from unknown outcome type raises `UnsupportedOutcomeError`.

## Pseudocode
1. Define `EventKind`, `EventSeverity`, and `EventStage` enums with explicit string wire values.
2. Define `BaseEvent` dataclass with required correlation fields and shared validation in `__post_init__`.
3. Define specialized event dataclasses (`IngestionSucceeded`, `IngestionFailed`, `SyncTriggered`, `StartupFailed`) that extend the base shape.
4. Implement `event_from_outcome(outcome, context)` to map stage outcomes to event dataclasses deterministically.
5. Implement `to_payload(event)` serializer used by UI and observability ports; reject unknown types early.
6. Document compatibility policy: adding a field is allowed only when defaulted and backwards-safe.

## Tests To Implement
- unit: enum wire values are stable, invalid payloads fail validation, and outcome-to-event mapping is deterministic.
- integration: ingestion pipeline emits canonical events consumed unchanged by UI and failure emission policies.



