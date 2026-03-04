---
id: infrastructure/runtime/ui/dialogs.py
origin_v1_files:
  - src/dpost/infrastructure/runtime_adapters/dialogs.py
lane: Infra-UI
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Dialog helpers and user-prompt composition.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/runtime_adapters/dialogs.py`.
- Legacy gist: Moves UI runtime adapter dialogs.py to dedicated UI infrastructure lane.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Dialog helpers and user-prompt composition.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Generic prompt specifications from application/runtime UI requests.
- Prompt templates, validation rules, and default options.
- Dialog backend interface (tkinter or compatible desktop prompt renderer).
- Timeout/cancel policy settings.

## Outputs
- Concrete dialog request payloads for UI backend.
- Normalized dialog result model (`accepted`, `rejected`, `cancelled`, optional selection).
- Prompt validation errors for malformed specifications.
- Prompt telemetry metadata (prompt id, response latency, cancel reason).

## Invariants
- Prompt ids are stable and unique per request.
- Dialog result always includes explicit terminal user action.
- Input validation occurs before backend prompt dispatch.
- Dialog helpers remain backend-agnostic and reusable.

## Failure Modes
- Malformed prompt spec raises `DialogSpecValidationError`.
- Unsupported prompt type raises `DialogTypeError`.
- Backend dispatch failure raises `DialogBackendError`.
- Timeout/cancel processing mismatch raises `DialogLifecycleError`.

## Pseudocode
1. Validate incoming prompt specification against supported prompt schema/types.
2. Compose backend-ready dialog payload including defaults and validation hints.
3. Dispatch prompt to backend adapter and await user response or timeout/cancel signal.
4. Normalize backend response into canonical dialog result model.
5. Emit prompt telemetry fields (prompt id, latency, terminal action).
6. Return typed errors for invalid specs/backend/lifecycle failures.

## Tests To Implement
- unit: prompt spec validation, backend payload composition, timeout/cancel normalization, and unsupported-type handling.
- integration: desktop UI orchestration uses dialog helpers to collect user decisions with consistent terminal action modeling.



