---
id: application/startup/context.py
origin_v1_files:
  - src/dpost/application/config/context.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Explicit context builder replacing ambient `current()/get_service()` access.

## Origin Gist
- Source mapping: `src/dpost/application/config/context.py`.
- Legacy gist: Replaces ambient global config access with explicit context injection.

## V2 Improvement Intent
- Transform posture: Retire/Replace.
- Target responsibility: Explicit context builder replacing ambient `current()/get_service()` access.
- Improvement goal: Replace legacy seams with explicit contract-driven behavior.
## Inputs
- `StartupSettings` produced by settings service.
- `StartupDependencies` produced by runtime dependency resolver.
- Launch metadata (`requested_mode`, `requested_profile`, boot timestamp, process id).
- Optional test overrides for deterministic clocks and temporary directories.

## Outputs
- Immutable `StartupContext` carrying settings, dependency bindings, and run metadata.
- Helper constructors (`build_startup_context`, `with_override`) for controlled derivation.
- Accessor functions that expose context by explicit parameter passing (no global cache).
- Validation report used by bootstrap before runtime launch.

## Invariants
- Context creation is explicit and single-shot per bootstrap run.
- `StartupContext` is immutable and serializable for diagnostics.
- All required dependency bindings are present before context is returned.
- No ambient `current()` singleton lookup exists in V2 startup flow.

## Failure Modes
- Missing dependency binding yields `StartupContextBindingError`.
- Invalid settings/dependency compatibility yields `StartupContextValidationError`.
- Duplicate override keys in test hooks yield `StartupContextOverrideError`.
- Attempt to mutate context fields after creation yields immutability error.

## Pseudocode
1. Define frozen `StartupContext` model containing settings snapshot, dependency container id map, and launch metadata.
2. Implement `build_startup_context(settings, dependencies, launch_meta)` with required-field and compatibility checks.
3. Implement `validate_startup_context(context)` to ensure mode-specific dependencies are present (for example UI adapter in desktop mode).
4. Implement explicit context pass-through helpers for bootstrap/composition entrypoints.
5. Remove ambient global access and require all startup consumers to accept `StartupContext` parameters.
6. Add serialization helper for startup diagnostics and failure reports.

## Tests To Implement
- unit: context builder rejects missing bindings and enforces immutability/explicit override rules.
- integration: bootstrap constructs one `StartupContext` and passes it through settings, composition, and app launch without global lookups.



