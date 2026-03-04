---
id: runtime/startup_dependencies.py
origin_v1_files:
  - src/dpost/runtime/startup_config.py
  - src/dpost/runtime/bootstrap.py
  - src/dpost/infrastructure/runtime_adapters/startup_dependencies.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Resolve startup dependencies from env/config files and runtime mode.

## Origin Gist
- Source mapping: `src/dpost/runtime/startup_config.py`, `src/dpost/runtime/bootstrap.py`, `src/dpost/infrastructure/runtime_adapters/startup_dependencies.py`.
- Legacy gist: Centralizes startup settings parsing and validation. Moves startup flow into explicit application startup boundary. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Move, Split.
- Target responsibility: Resolve startup dependencies from env/config files and runtime mode.
- Improvement goal: Decompose orchestration into focused modules/stages with tighter ownership. Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- `StartupSettings` and selected runtime mode/profile.
- Process environment and filesystem access points needed for adapter creation.
- Dependency override hooks for tests and deterministic runs.
- Availability probes for optional subsystems (desktop UI backend, sync backend, plugin modules).

## Outputs
- Immutable `StartupDependencies` container with adapter factories and primitive runtime services.
- Dependency resolution diagnostics (selected backend names, disabled features, warnings).
- Optional deferred/lazy factories for heavyweight adapters.
- Typed dependency resolution errors for bootstrap handling.

## Invariants
- Resolver contains no business logic; it only maps settings to dependency providers.
- Resolved dependencies are explicit and serializable in diagnostics.
- Mode/profile decisions are deterministic for identical settings.
- Lazy dependencies are marked and initialized only when composition requests them.

## Failure Modes
- Missing required environment values raises `DependencyResolutionError`.
- Unsupported backend token raises `DependencyBackendSelectionError`.
- Import/load failure for requested subsystem raises `DependencyImportError`.
- Mutually incompatible dependency combination raises `DependencyCompatibilityError`.

## Pseudocode
1. Read validated settings and compute backend selection tokens for each dependency family.
2. Build factories for filesystem, clock, event sink, UI, sync, storage, and plugin discovery dependencies.
3. Validate mode-specific requirements (for example desktop mode requires desktop-capable UI backend).
4. Attach availability warnings for optional subsystems and mark lazy factories where allowed.
5. Package all factories and metadata into immutable `StartupDependencies`.
6. Return typed success/failure result to bootstrap without constructing application services directly.

## Tests To Implement
- unit: backend selection matrix by mode/profile, compatibility checks, and lazy dependency markers.
- integration: bootstrap + composition consume `StartupDependencies` and fail predictably when required backends are unavailable.



