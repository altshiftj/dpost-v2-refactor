---
id: runtime/composition.py
origin_v1_files:
  - src/dpost/runtime/composition.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Build dependency graph, wire ports to adapters, return app runtime object.

## Origin Gist
- Source mapping: `src/dpost/runtime/composition.py`.
- Legacy gist: Composition root wires contracts to adapters for V2.

## V2 Improvement Intent
- Transform posture: Rewrite.
- Target responsibility: Build dependency graph, wire ports to adapters, return app runtime object.
- Improvement goal: Rebuild the module around cleanroom contracts while preserving intended outcomes.
## Inputs
- Validated `StartupContext` (settings + dependencies + launch metadata).
- Adapter factories for UI, storage, sync, observability, and plugin host.
- Contract protocol modules (`ports`, `events`, `plugin_contracts`, `context`).
- Optional test doubles for deterministic composition tests.

## Outputs
- Fully wired `DPostApp` runtime object.
- `PortBindings` snapshot showing concrete adapter bound to each required port.
- Startup diagnostics summary of selected adapters and enabled capabilities.
- Lifecycle bundle with `shutdown_all()` hook for bootstrap rollback/teardown.

## Invariants
- Every required application port is bound exactly once.
- Application modules depend only on contract interfaces, never infrastructure class imports.
- Composition order is deterministic and mode-aware.
- Adapter initialization failures are surfaced immediately; no partial silent fallback.

## Failure Modes
- Missing required adapter factory raises `CompositionBindingError`.
- Adapter initialization or healthcheck failure raises `CompositionInitializationError`.
- Duplicate port binding attempt raises `CompositionDuplicateBindingError`.
- Invalid plugin host/catalog construction raises `CompositionPluginBindingError`.

## Pseudocode
1. Build observability adapters first so downstream startup can emit structured diagnostics.
2. Instantiate storage, sync, UI, event, and plugin host adapters from mode-aware factories.
3. Validate adapter set against `ports` contract matrix and fail fast on missing/duplicate bindings.
4. Construct application services (`session_manager`, `records_service`, ingestion engine, runtime app) using ports only.
5. Run lightweight adapter healthchecks and collect composition diagnostics.
6. Return `DPostApp` plus lifecycle bundle and binding snapshot to bootstrap.

## Tests To Implement
- unit: binding validator catches missing/duplicate ports and mode-specific adapter selection logic.
- integration: bootstrap + composition produce a runnable `DPostApp` in headless and desktop modes with contract-only dependencies.



