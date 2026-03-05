# Architecture Contract

## Purpose

- Define enforceable dependency and ownership rules for the V2 runtime.
- Prevent drift across domain/application/infrastructure/plugin/runtime layers.

## Layer Dependency Rules

1. Domain layer (`src/dpost_v2/domain/**`):
- can use stdlib and domain-local modules
- must not import application/infrastructure/runtime/plugin modules
- must remain side-effect free

2. Application layer (`src/dpost_v2/application/**`):
- can depend on domain and application contracts
- orchestrates use-case flows (startup, ingestion, runtime/session, records)
- must not hard-depend on concrete infrastructure implementations

3. Infrastructure layer (`src/dpost_v2/infrastructure/**`):
- can depend on application contracts and external SDKs
- owns adapter implementations (storage/sync/observability/runtime UI)
- must not own domain decision policy

4. Plugin layer (`src/dpost_v2/plugins/**`):
- provides extension implementations against plugin contracts
- owns discovery/host/profile selection
- must not own global runtime composition policy

5. Runtime layer (`src/dpost_v2/runtime/**`):
- owns dependency resolution and composition root wiring
- must not absorb domain policy or plugin business logic

## Runtime Composition Rules

- Composition is centralized in `src/dpost_v2/runtime/composition.py`.
- Startup dependency selection is centralized in
  `src/dpost_v2/runtime/startup_dependencies.py`.
- Startup orchestration is centralized in
  `src/dpost_v2/application/startup/bootstrap.py`.
- Runtime mode policy is V2-only (`headless`/`desktop`).
- Transition architecture modes (`v1`/`shadow`) are retired and are not valid
  targets for active runbooks/checks.

## Port/Adapter Rules

- Application contracts in `src/dpost_v2/application/contracts/ports.py` are the
  only stable adapter boundary.
- Composition must validate complete port bindings before runtime launch.
- Adapter selection must be explicit (`noop`/`kadi` sync backend policy).
- Optional backend SDKs remain optional dependencies (for example `kadi`).

## Plugin Contract Rules

- Plugin contracts are defined in
  `src/dpost_v2/application/contracts/plugin_contracts.py`.
- Discovery namespaces are:
  - `dpost_v2.plugins.devices`
  - `dpost_v2.plugins.pcs`
- Device plugin exports must include metadata/capabilities/settings validation
  and processor creation.
- PC plugin exports must include metadata/capabilities/sync adapter creation and
  sync payload preparation.

## Documentation Rules

Architecture-impacting changes must update, in the same change set:

- relevant plan/report/checklist artifacts
- architecture baseline and/or responsibility catalog when ownership changes
- extension contract doc when contributor-facing contracts change
- glossary when new internal terms are introduced

## Test Isolation Rules

- Active test target is `tests/dpost_v2/`.
- Legacy test lanes (`tests/unit`, `tests/integration`, `tests/manual`) are
  archived and excluded from active CI requirements.
- Archived compatibility tests may use marker `legacy`.

## Compliance Gate

A delivery slice cannot close unless impacted rules are either:

- satisfied, or
- explicitly amended here with rationale and ADR linkage.
