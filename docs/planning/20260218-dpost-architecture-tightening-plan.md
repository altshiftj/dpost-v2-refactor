# dpost Architecture Tightening and Migration Plan

## Goal
- Migrate `ipat_watchdog` to a new open-source project identity (`dpost`) with clearer boundaries, lower global state coupling, and a more standardized architecture without breaking existing behavior.

## Decisions Locked (2026-02-18)
- Runtime posture: headless-first.
- Sync architecture: optional adapters to support multiple databases/ELNs.
- Planning cadence: execute via a dated board with owners and target dates.

## Non-Goals
- No broad feature additions during migration.
- No plugin logic rewrites unless required for boundary compliance.
- No immediate retirement of Tkinter UX; desktop integration follows headless stabilization.

## Constraints
- Current behavior in file routing, plugin resolution, and sync flows must remain stable.
- Existing plugin integrations and test flows must keep working through transition.
- Migration should be incremental and reviewable, not a one-shot rewrite.

## Approach
- Use phased migration with acceptance gates per phase.
- First lock behavior via tests and characterization checks.
- Build a new package structure around explicit boundaries:
- `domain` for core models/rules
- `application` for orchestration/use-cases
- `infrastructure` for adapters (filesystem, observability, runtime glue, optional sync backends)
- `plugins` for device/PC integrations
- Define a sync adapter port early and move Kadi to an optional adapter implementation.
- Bring desktop runtime back only after headless mode is green and stable.
- Move modules gradually, with compatibility shims only where required.

## Documentation Backbone
- Architecture baseline:
- `docs/architecture/architecture-baseline.md`
- Responsibilities and ownership:
- `docs/architecture/responsibility-catalog.md`
- Architecture decision records:
- `docs/architecture/adr/`
- Vocabulary source of truth:
- `GLOSSARY.csv`
- Rule: each closed migration phase must update affected architecture docs in the same phase.

## Milestones
1. Baseline and Architecture Contract Freeze
2. dpost Package Spine and Headless Composition Root
3. Optional Sync Adapter Interface and Packaging
4. Configuration Consolidation
5. Processing Pipeline Decomposition
6. Plugin and Discovery Hardening
7. Desktop Runtime Integration
8. Final Cutover and Cleanup

## Phased Plan with Acceptance Criteria

### Phase 1: Baseline and Architecture Contract Freeze
- Scope:
- Freeze expected behavior with characterization tests for bootstrap, processing, plugin loading, and sync side effects.
- Add an architecture contract document describing allowed dependency directions.
- Acceptance criteria:
- Existing unit/integration tests pass unchanged.
- Characterization tests exist for current critical flows (bootstrap, file process manager, plugin load by name, immediate sync).
- Architecture contract doc exists and is referenced in developer docs.

### Phase 2: dpost Package Spine and Headless Composition Root
- Scope:
- Introduce new package root for `dpost` while keeping old entrypoint operational during transition.
- Create one composition root responsible for wiring config, plugins, sync port, and observers for headless runtime.
- Establish test isolation so `dpost` migration tests can evolve without destabilizing legacy contract tests.
- Acceptance criteria:
- New `dpost` headless entrypoint runs in a smoke test path.
- Old entrypoint still works during migration window.
- No new module-level singletons introduced outside explicitly approved runtime wiring.
- Migration tests run independently via marker selection.

### Phase 3: Optional Sync Adapter Interface and Packaging
- Scope:
- Define a sync adapter port in the application boundary.
- Move current Kadi implementation behind an optional adapter package path.
- Support adapter selection via explicit configuration.
- Acceptance criteria:
- Core application can run without importing Kadi adapter modules.
- Kadi adapter remains functionally equivalent when selected.
- At least one no-op/mock adapter path exists for headless local usage and tests.
- Adapter selection and startup errors are covered by tests.

### Phase 4: Configuration Consolidation
- Scope:
- Converge on one authoritative config path (schema/service) and remove operational fallback reliance on legacy constants.
- Normalize environment and path configuration policy for portability.
- Acceptance criteria:
- Core runtime path resolution uses config service only.
- `filesystem_utils` and related modules no longer depend on fallback global constants in operational paths.
- Config tests cover both default and explicit env/path scenarios.

### Phase 5: Processing Pipeline Decomposition
- Scope:
- Split orchestration responsibilities in `FileProcessManager` into focused application services:
- resolve device
- stabilize artifact
- preprocess
- route/rename decision
- persist record and sync trigger
- Keep external behavior and typed result models stable.
- Acceptance criteria:
- New stage-oriented services are in place with unit tests.
- Integration tests for multi-device and multi-processor flows remain green.
- Cyclomatic and file-size pressure in the orchestration module is reduced materially.

### Phase 6: Plugin and Discovery Hardening
- Scope:
- Standardize plugin package hygiene (init naming, stale directories, metadata consistency).
- Align optional dependency groups and plugin inventory.
- Strengthen plugin discovery error messages and validation checks.
- Acceptance criteria:
- Plugin package structure is consistent and import-clean.
- No stale plugin directories without source modules remain.
- Plugin discovery and mapping tests pass with current intended plugin set.

### Phase 7: Desktop Runtime Integration
- Scope:
- Re-introduce desktop runtime wiring on top of headless-validated application services.
- Keep interaction ports and adapters, with runtime mode selected at composition root.
- Acceptance criteria:
- Headless mode remains green while desktop wiring is added.
- Desktop mode preserves current dialog/session behavior.
- Both runtime modes have smoke tests.

### Phase 8: Final Cutover and Cleanup
- Scope:
- Switch canonical package, scripts, and docs from `ipat_watchdog` to `dpost`.
- Remove obsolete compatibility layer after validation window.
- Acceptance criteria:
- `pyproject.toml` metadata and scripts reflect `dpost`.
- Legacy paths are removed or explicitly deprecated with clear sunset date.
- Release checklist is complete and docs are synchronized.

## Dependencies
- Owner assignment and target dates for each phase.
- Agreement on plugin strategy over time: in-repo vs externally packaged entry points.

## Risks and Mitigations
- Risk: Behavioral regressions in file routing/sync.
- Mitigation: Characterization tests before major moves; phase gates block cutover.

- Risk: Incremental dual-entrypoint complexity.
- Mitigation: Keep one composition root and thin wrappers only.

- Risk: Plugin breakage due to structural cleanup.
- Mitigation: Plugin inventory tests and explicit per-plugin smoke checks.

## Test Plan
- Run full unit and integration suites at each phase gate.
- Add targeted smoke tests for:
- new `dpost` entrypoint bootstrap
- headless runtime path
- adapter-selection startup path
- plugin discovery by canonical names
- Use repository-standard commands:
- `python -m pytest`
- `python -m ruff check .`

## Rollout / Validation
- Use phased cutover with explicit gate sign-off after each phase.
- Keep old entrypoint temporarily while validating new package entrypoint.
- Promote `dpost` as canonical only after:
- full test pass
- manual runtime checks complete
- docs and packaging metadata finalized
