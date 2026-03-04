---
id: application/contracts/ports.py
origin_v1_files:
  - src/dpost/application/ports/interactions.py
  - src/dpost/application/ports/sync.py
  - src/dpost/application/ports/ui.py
lane: Contracts-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Protocol interfaces for UI, storage, sync, events, plugin host, clock, filesystem.

## Origin Gist
- Source mapping: `src/dpost/application/ports/interactions.py`, `src/dpost/application/ports/sync.py`, `src/dpost/application/ports/ui.py`.
- Legacy gist: Converges port contract interactions.py into unified ports surface. Converges port contract sync.py into unified ports surface. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Merge.
- Target responsibility: Protocol interfaces for UI, storage, sync, events, plugin host, clock, filesystem.
- Improvement goal: Consolidate duplicated logic into a single canonical owner.
## Inputs
- Application use cases from startup/runtime/ingestion that require side effects.
- Contract models (`RuntimeContext`, events, candidates, failure outcomes) crossing the boundary.
- Adapter capability constraints (headless vs desktop UI, noop vs kadi sync, sqlite vs in-memory store).
- Operational concerns (timeouts, cancellation, and retry semantics) represented as typed arguments.

## Outputs
- Port protocols: `UiPort`, `EventPort`, `RecordStorePort`, `FileOpsPort`, `SyncPort`, `PluginHostPort`, `ClockPort`, `FilesystemPort`.
- Typed request/response envelopes for operations that can partially fail.
- Shared adapter error taxonomy expected by application policies.
- Minimal adapter lifecycle hooks (`initialize`, `healthcheck`, `shutdown`) where needed.

## Invariants
- Application layer imports only these ports, never concrete adapter modules.
- All ports are synchronous-or-async explicit; no dual-mode method signatures.
- Port methods document idempotency expectations for retryable operations.
- Adapter exceptions crossing the boundary are normalized into contract-defined error types.

## Failure Modes
- Missing adapter implementation for a required port raises `PortBindingError` at composition time.
- Adapter returns incompatible response model raises `PortResponseContractError`.
- Timeout/cancellation from adapters maps to `PortTimeoutError`/`PortCancelledError`.
- Healthcheck failure during startup prevents runtime launch and emits startup failure event.

## Pseudocode
1. Enumerate all side-effect operations required by application modules and group them by port owner.
2. Define protocol interfaces per port with explicit method signatures and typed return contracts.
3. Define shared error classes and response envelopes for recoverable vs terminal adapter failures.
4. Define composition-time `validate_port_bindings(bindings)` guard used by runtime composition root.
5. Document idempotency and retry expectations per method so ingestion retry planner can rely on port behavior.
6. Export port protocol names from a single module to prevent parallel-lane signature drift.

## Tests To Implement
- unit: protocol conformance checks for mock adapters and validation of required binding set.
- integration: composition root rejects missing bindings and ingestion policies handle normalized port failures uniformly across storage/sync/ui ports.



