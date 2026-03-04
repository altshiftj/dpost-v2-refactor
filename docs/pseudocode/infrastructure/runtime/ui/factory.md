---
id: infrastructure/runtime/ui/factory.py
origin_v1_files:
  - src/dpost/infrastructure/runtime_adapters/ui_factory.py
lane: Infra-UI
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Select UI adapter implementation for headless/desktop mode.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/runtime_adapters/ui_factory.py`.
- Legacy gist: Moves UI runtime adapter ui_factory.py to dedicated UI infrastructure lane.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Select UI adapter implementation for headless/desktop mode.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Runtime settings controlling UI mode (`headless`, `desktop`, backend preference).
- Environment capability probes (display availability, tkinter availability).
- UI adapter constructors for supported backends.
- Optional override for tests.

## Outputs
- Concrete `UiPort` adapter instance.
- Selection descriptor documenting chosen adapter and fallback reason.
- Typed selection/setup errors for unsupported or unavailable modes.
- Adapter lifecycle hooks (initialize, shutdown).

## Invariants
- Selection is deterministic for identical settings and capability probes.
- Factory returns only `UiPort`-conformant adapters.
- Unsupported desktop backends do not silently select unsafe alternatives.
- Headless mode always resolves without GUI dependency requirements.

## Failure Modes
- Unknown UI mode token raises `UiFactoryModeError`.
- Requested desktop backend unavailable raises `UiFactoryBackendUnavailableError`.
- Adapter initialization failure raises `UiFactoryInitializationError`.
- Adapter contract mismatch raises `UiFactoryContractError`.

## Pseudocode
1. Read UI mode/backend settings and run capability probes.
2. Select candidate adapter constructor via deterministic mode/backend matrix.
3. Validate constructor availability and instantiate adapter.
4. Run adapter initialization and contract conformance check.
5. Build selection descriptor with fallback or failure diagnostics.
6. Return initialized adapter + descriptor to composition root.

## Tests To Implement
- unit: mode/backend selection matrix, capability-probe fallbacks, and initialization/contract failure mapping.
- integration: runtime composition selects headless or desktop adapters correctly under CI vs desktop environment conditions.



