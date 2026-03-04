---
id: infrastructure/sync/noop.py
origin_v1_files:
  - src/dpost/infrastructure/sync/noop.py
lane: Infra-Sync
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- No-op sync backend for offline/testing mode.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/sync/noop.py`.
- Legacy gist: Retains sync adapter module noop.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: No-op sync backend for offline/testing mode.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Sync requests (record id, payload metadata, operation type) from application runtime services.
- Correlation context for observability.
- No-op policy configuration (reason message, optional simulate-latency flag).
- Healthcheck/startup hooks.

## Outputs
- Structured sync response with terminal type `skipped_noop`.
- Deterministic reason code indicating offline/noop mode.
- Optional observability event payloads for skipped sync calls.
- Healthcheck response indicating adapter availability.

## Invariants
- Adapter performs no network or remote side effects.
- Same input request always produces same `skipped_noop` outcome.
- Adapter response shape matches `SyncPort` contract exactly.
- No-op adapter remains safe for tests and offline runtime mode.

## Failure Modes
- Malformed sync request payload raises `NoopSyncInputError`.
- Contract mismatch in request type raises `NoopSyncContractError`.
- Optional simulated latency cancellation yields `NoopSyncCancelledError`.
- Healthcheck misuse before initialization yields `NoopSyncLifecycleError`.

## Pseudocode
1. Validate incoming sync request against `SyncPort` request contract.
2. Build deterministic skipped outcome with configured reason code/message.
3. Optionally emit observability trace/metric for skipped sync.
4. Respect simulated latency/cancellation flags if configured for tests.
5. Return `skipped_noop` response without external side effects.
6. Implement simple healthcheck/initialize/shutdown lifecycle hooks.

## Tests To Implement
- unit: deterministic skipped outcomes, malformed input handling, and lifecycle hook behavior.
- integration: post-persist immediate sync paths in offline mode receive `skipped_noop` outcomes and continue without failures.



