---
id: infrastructure/runtime/ui/headless.py
origin_v1_files:
  - src/dpost/infrastructure/runtime_adapters/headless_ui.py
lane: Infra-UI
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Headless UI adapter for CI/automation.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/runtime_adapters/headless_ui.py`.
- Legacy gist: Moves UI runtime adapter headless_ui.py to dedicated UI infrastructure lane.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Headless UI adapter for CI/automation.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Normalized UI requests from `UiPort` shim (`notify`, `prompt`, `status` updates).
- Headless behavior settings (default prompt responses, verbosity level, fail-on-prompt flags).
- Correlation metadata for log-friendly output.
- Optional output sink for CI logs.

## Outputs
- Deterministic non-interactive UI responses.
- Structured prompt result objects (auto-accept, auto-cancel, configured defaults).
- Log-friendly status/error messages.
- Typed headless adapter errors for invalid unsupported request patterns.

## Invariants
- Adapter never blocks waiting for interactive user input.
- Same request + config produces same response in headless mode.
- All prompt responses explicitly indicate auto-response origin.
- Headless adapter remains safe in environments without GUI libraries.

## Failure Modes
- Prompt request requiring mandatory manual selection with no default yields `HeadlessUiPromptResolutionError`.
- Invalid payload schema yields `HeadlessUiInputError`.
- Output sink write failure yields `HeadlessUiSinkError`.
- Lifecycle misuse (call before init/after shutdown) yields `HeadlessUiLifecycleError`.

## Pseudocode
1. Initialize headless adapter with deterministic default response policy.
2. Handle notify/status calls by writing structured messages to configured sink.
3. Handle prompt calls using configured defaults or explicit fail-on-prompt policy.
4. Build normalized prompt results with auto-response metadata.
5. Map sink/input/lifecycle errors to typed headless adapter errors.
6. Provide no-op shutdown cleanup for composition lifecycle compatibility.

## Tests To Implement
- unit: deterministic auto-response behavior, fail-on-prompt enforcement, and sink error mapping.
- integration: runtime in headless mode completes ingestion flows without blocking UI calls and records deterministic prompt outcomes.



