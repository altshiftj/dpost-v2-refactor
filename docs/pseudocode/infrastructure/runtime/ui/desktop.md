---
id: infrastructure/runtime/ui/desktop.py
origin_v1_files:
  - src/dpost/infrastructure/runtime_adapters/desktop_ui.py
lane: Infra-UI
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Desktop UI orchestration and shared desktop view model wiring.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/runtime_adapters/desktop_ui.py`.
- Legacy gist: Moves UI runtime adapter desktop_ui.py to dedicated UI infrastructure lane.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Desktop UI orchestration and shared desktop view model wiring.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Application runtime events/status updates destined for desktop UI.
- Dialog helper APIs and tkinter adapter interfaces.
- Desktop view model/state definitions.
- User action callbacks (acknowledge, retry, skip, cancel).

## Outputs
- Updated desktop view model state and rendered UI actions.
- Routed prompt requests to dialog/tkinter components.
- Normalized user action events returned to application layer.
- Desktop orchestration diagnostics and typed errors.

## Invariants
- Desktop orchestration coordinates adapters but does not implement business policy.
- View model updates are deterministic for identical event sequences.
- Prompt flows always return explicit user action or cancel result.
- Event-to-view mapping remains compatible with `UiPort` contracts.

## Failure Modes
- Invalid event/view payload shape raises `DesktopUiPayloadError`.
- Dialog/tkinter adapter failure raises `DesktopUiAdapterError`.
- View model state transition mismatch raises `DesktopUiStateError`.
- Callback execution failure yields `DesktopUiCallbackError`.

## Pseudocode
1. Initialize desktop view model and bind dialog/tkinter adapter dependencies.
2. Consume runtime UI events and map each to view model transitions.
3. Delegate prompt-producing events to dialog helper/tkinter components.
4. Normalize user interactions into `UiPort` action results for application runtime.
5. Handle adapter/callback failures with typed desktop UI errors and fallback notifications.
6. Emit desktop orchestration diagnostics for observability.

## Tests To Implement
- unit: event-to-view transition mapping, adapter delegation, and user action normalization.
- integration: desktop runtime mode orchestrates dialogs/tkinter through desktop layer and returns deterministic actions to application runtime.



