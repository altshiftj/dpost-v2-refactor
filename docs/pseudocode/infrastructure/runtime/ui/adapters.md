---
id: infrastructure/runtime/ui/adapters.py
origin_v1_files:
  - src/dpost/infrastructure/runtime_adapters/ui_adapters.py
lane: Infra-UI
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- UI adapter shims implementing application UI port.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/runtime_adapters/ui_adapters.py`.
- Legacy gist: Moves UI runtime adapter ui_adapters.py to dedicated UI infrastructure lane.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: UI adapter shims implementing application UI port.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- UI port calls from application layer (`notify`, `prompt`, `show_status`, `report_error`).
- Backend-specific adapter objects (headless, desktop/tkinter).
- UI payload models and optional localization/theme settings.
- Correlation metadata for user-visible event linkage.

## Outputs
- Unified `UiPort` shim layer exposing consistent method signatures.
- Adapter result envelopes for prompts/notifications.
- Normalized UI errors mapped from backend-specific failures.
- Capability matrix indicating supported prompt/interaction types.

## Invariants
- Shim layer does not contain business rule logic.
- All adapters return normalized result types with explicit cancel/error states.
- Unsupported interaction types are reported as typed errors, not silently ignored.
- Method semantics remain consistent regardless of underlying backend.

## Failure Modes
- Backend adapter missing required method yields `UiAdapterContractError`.
- Payload validation failure yields `UiAdapterInputError`.
- Backend runtime exception yields `UiAdapterRuntimeError`.
- Unsupported capability request yields `UiAdapterCapabilityError`.

## Pseudocode
1. Define shared shim interface matching application `UiPort` contract.
2. Implement backend wrapper classes translating generic UI requests into backend-specific calls.
3. Validate incoming payloads and map backend responses to normalized result envelopes.
4. Map backend exceptions/cancellations into typed UI adapter errors/results.
5. Expose capability matrix for runtime decisions before prompt calls.
6. Keep adapter wrappers stateless except for backend handle references.

## Tests To Implement
- unit: payload/result normalization, capability reporting, and backend exception mapping.
- integration: runtime app invokes `UiPort` through adapter shims and receives consistent responses across headless and desktop backends.



