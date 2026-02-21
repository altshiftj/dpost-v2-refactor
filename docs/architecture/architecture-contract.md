# Architecture Contract

## Purpose
- Define enforceable dependency and ownership rules for the `ipat_watchdog` -> `dpost` migration.
- Prevent architecture drift while modules are moved and decomposed.

## Layer Dependency Rules
1. Domain layer:
- can depend on Python standard library and pure domain models/utilities.
- must not depend on infrastructure SDKs, UI frameworks, or runtime wiring.

2. Application layer:
- can depend on domain and application ports.
- can orchestrate use-cases and workflows.
- must not depend directly on concrete infrastructure implementations by default.

3. Infrastructure layer:
- can depend on domain/application ports and external SDKs/APIs.
- implements adapters for filesystem, sync backends, UI/runtime glue, observability.
- must not contain core domain decision logic.

4. Plugin layer:
- can provide device/PC specific implementations against plugin contracts.
- must not perform global runtime composition or cross-layer wiring.

## Runtime Composition Rules
- Dependency wiring happens in one composition root.
- Avoid new module-level singletons outside explicit runtime composition.
- Runtime mode selection (headless/desktop) is configured at composition root.

## Framework Kernel Boundary (Phase 3)
- The dpost kernel boundary is currently limited to these framework surfaces:
- `src/dpost/runtime/composition.py` (startup composition and adapter/profile selection)
- `src/dpost/runtime/bootstrap.py` (native startup contracts and runtime bootstrap boundary API)
- `src/dpost/application/services/runtime_startup.py` (application-level runtime startup orchestration)
- `src/dpost/runtime/startup_config.py` (startup config/env-to-settings boundary)
- `src/dpost/application/ports/sync.py` (sync adapter port contract)
- `src/dpost/plugins/reference.py` (reference plugin profile contract)
- `src/dpost/plugins/profile_selection.py` (plugin profile selection boundary)
- Kernel composition paths can map explicit profile names to startup settings.
- Kernel runtime modules should depend on dpost-owned bootstrap contracts, not
  direct legacy bootstrap module imports.
- Runtime composition should delegate plugin/config resolution to explicit
  boundary helpers and orchestration services instead of embedding env parsing.
- Kernel composition paths must not import concrete backend SDK modules directly.
- Concrete backend and plugin integrations stay behind infrastructure/plugin boundaries.

## Framework-first Sequencing Rules
- Build framework kernel contracts before migrating concrete integrations.
- Validate framework with reference implementations first (for example noop adapter, test plugin flow).
- Migrate concrete adapters/plugins only after kernel contract tests are green.

## Sync Adapter Rules
- Application code uses sync adapter port abstractions.
- Concrete backends (for example Kadi) are infrastructure adapters.
- Adapter selection is explicit and validated at startup.
- Backend-specific SDK dependencies stay optional in packaging and are enabled
  through explicit optional dependency groups.
- dpost sync adapter kernel contract currently lives in:
- `src/dpost/application/ports/sync.py`
- dpost reference adapter for kernel validation currently lives in:
- `src/dpost/infrastructure/sync/noop.py`

## Naming Clarity Rules
- Prefer intention-revealing names for orchestration-stage functions and variables.
- Avoid generic stage-boundary names (for example `item`, `data`, `thing`) when
  a domain term exists (`request`, `candidate`, `context`, `decision`,
  `result`).
- Function names should reflect side effects: route/decision functions should
  not imply persistence or sync side effects; persistence/sync functions should
  state that intent directly.

## Documentation Rules
- Architecture-impacting changes require:
- relevant report/plan/checklist updates
- ADR update when direction or policy changes
- responsibility catalog updates when ownership changes
- glossary updates for new project-defined terms

## Test Isolation Rules
- Migration-cutover tests live under `tests/migration/` and are tagged `migration`.
- Existing behavior contract tests are tagged `legacy`.
- Changes that affect both paths should include marker-specific verification runs.

## Compliance Gate
- A migration phase cannot close until impacted contract rules are either:
- satisfied, or
- explicitly amended in this contract with rationale and ADR reference.
