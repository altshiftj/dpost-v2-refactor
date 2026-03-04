---
id: application/startup/bootstrap.py
origin_v1_files:
  - src/dpost/application/services/runtime_startup.py
  - src/dpost/runtime/bootstrap.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Startup orchestration sequence: load settings, build composition, launch runtime.

## Origin Gist
- Source mapping: `src/dpost/application/services/runtime_startup.py`, `src/dpost/runtime/bootstrap.py`.
- Legacy gist: Unifies runtime startup orchestration into bootstrap module. Moves startup flow into explicit application startup boundary.

## V2 Improvement Intent
- Transform posture: Merge, Split.
- Target responsibility: Startup orchestration sequence: load settings, build composition, launch runtime.
- Improvement goal: Decompose orchestration into focused modules/stages with tighter ownership. Consolidate duplicated logic into a single canonical owner.
## Inputs
- `BootstrapRequest` from `__main__`.
- `SettingsService`, `StartupDependenciesResolver`, and runtime composition builder callables.
- Event/log ports for startup diagnostics emission.
- Process lifecycle hooks (`shutdown`, `signal handlers`) injected from runtime boundary.

## Outputs
- `BootstrapResult` describing launched runtime handle or normalized startup failure.
- Live application runtime instance when startup succeeds.
- Deterministic startup event stream entries (`startup_started`, `startup_failed`, `startup_succeeded`).
- Exit decision metadata consumed by `__main__`.

## Invariants
- Startup sequence is fixed: settings -> dependencies -> context -> composition -> app launch.
- Bootstrap owns orchestration only; no domain rule evaluation is done here.
- Any partial startup initializes a matching cleanup path.
- Errors are normalized before crossing to `__main__`.

## Failure Modes
- Settings load failure halts startup before dependency resolution.
- Dependency resolution failure halts before composition and emits startup failure event.
- Composition binding failure halts before app launch and runs cleanup.
- App launch failure after partial initialization triggers bounded rollback and typed failure outcome.

## Pseudocode
1. Emit `startup_started` event with request metadata and trace id.
2. Load and validate settings via settings service; return failure result immediately on error.
3. Resolve startup dependencies for requested mode/profile; validate required bindings.
4. Build `StartupContext` and call composition root to obtain a fully wired runtime app.
5. Launch runtime app and attach shutdown hooks; emit `startup_succeeded` on success.
6. On any exception, map error to startup failure outcome, emit failure event, execute cleanup, and return failure result.

## Tests To Implement
- unit: orchestration ordering, short-circuit behavior on each failure point, and cleanup invocation contract.
- integration: end-to-end bootstrap from `__main__` launches app in valid mode and emits normalized startup events on failure paths.



