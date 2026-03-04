---
id: infrastructure/sync/kadi.py
origin_v1_files:
  - src/dpost/infrastructure/sync/kadi.py
  - src/dpost/infrastructure/sync/kadi_manager.py
lane: Infra-Sync
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Kadi sync adapter implementing SyncPort with structured outcomes.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/sync/kadi.py`, `src/dpost/infrastructure/sync/kadi_manager.py`.
- Legacy gist: Consolidates Kadi sync integration into one adapter module.

## V2 Improvement Intent
- Transform posture: Merge.
- Target responsibility: Kadi sync adapter implementing SyncPort with structured outcomes.
- Improvement goal: Consolidate duplicated logic into a single canonical owner.
## Inputs
- Sync requests from post-persist runtime services (record metadata, payload pointers, operation mode).
- Kadi connection settings (endpoint, credentials, workspace/project ids, timeout/retry knobs).
- Correlation context and idempotency key.
- Optional adapter lifecycle hooks (initialize token refresh, shutdown cleanup).

## Outputs
- Typed sync response (`synced`, `queued`, `conflict`, `failed`) with remote reference metadata.
- Error classification payload for retry planner and immediate sync error emitter.
- Request/response diagnostics (HTTP/status code mapping, latency, remote ids).
- Healthcheck/status output for startup validation.

## Invariants
- Adapter request serialization is deterministic for identical sync inputs.
- Idempotency key propagation is enforced for retry-safe operations.
- All external errors are mapped to `SyncPort` contract error types.
- Adapter does not perform domain decisions; it only executes sync operations.

## Failure Modes
- Authentication or credential failure yields `KadiSyncAuthError`.
- Network timeout/connectivity failure yields `KadiSyncNetworkError`.
- Remote conflict response yields `KadiSyncConflictError`.
- Unexpected response payload/shape yields `KadiSyncResponseError`.

## Pseudocode
1. Initialize Kadi client/session using configured endpoint and credentials.
2. Build sync request payload from contract input and attach idempotency/correlation headers.
3. Execute remote call and capture transport/status diagnostics.
4. Map remote/transport outcomes to typed `SyncPort` response categories.
5. Normalize remote metadata (remote id/version/timestamp) into response model.
6. Expose healthcheck and graceful shutdown behavior for composition/bootstrap.

## Tests To Implement
- unit: request serialization, error mapping (auth/network/conflict), idempotency header propagation, and response normalization.
- integration: post-persist immediate sync and deferred sync flows call Kadi adapter and receive stable typed outcomes across retry and conflict scenarios.



