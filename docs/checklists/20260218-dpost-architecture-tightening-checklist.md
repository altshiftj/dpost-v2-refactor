# dpost Architecture Tightening Checklist

## Section: Cross-cutting Documentation Governance
- Why this matters: Architectural quality degrades quickly when decisions and ownership boundaries are not documented as changes land.

### Checklist
- [ ] Keep `docs/architecture/architecture-baseline.md` aligned with current structure.
- [ ] Keep `docs/architecture/responsibility-catalog.md` aligned with ownership changes.
- [ ] Add or update ADR entries in `docs/architecture/adr/` for major architectural decisions.
- [ ] Add/update project-defined terms in `GLOSSARY.csv` when vocabulary changes.
- [ ] Link architecture-affecting PRs to relevant plan/checklist/report/ADR docs.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 1 Baseline and Contract Freeze
- Why this matters: Stable migration requires a locked behavioral baseline and clear dependency rules before refactoring.

### Checklist
- [ ] Confirm full baseline test pass.
- [ ] Add or verify characterization test for bootstrap startup path.
- [ ] Add or verify characterization test for plugin load by canonical name.
- [ ] Add or verify characterization test for processing pipeline happy path.
- [ ] Add or verify characterization test for immediate sync behavior for processed records.
- [ ] Add architecture contract doc describing allowed dependency directions.
- [ ] Link contract doc from developer-facing documentation.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 2 dpost Spine and Headless Composition Root
- Why this matters: Headless-first delivery establishes an automation-safe core before UI coupling is reintroduced.

### Checklist
- [x] Create new `dpost` package skeleton with explicit layers.
- [x] Implement a single composition root for dependency wiring.
- [x] Add a new headless `dpost` entrypoint wired through composition root.
- [x] Keep legacy entrypoint operational during transition.
- [x] Add smoke test for new headless entrypoint startup.

### Completion Notes
- How it was done: Added `src/dpost` scaffolding (`domain`, `application`,
  `infrastructure`, `plugins`, `runtime`), wired `dpost` script in
  `pyproject.toml`, added `tests/migration/test_dpost_main.py`, and validated
  with marker-aware pytest runs.

---

## Section: Phase 3 Optional Sync Adapter Interface
- Why this matters: Optional sync adapters enable database/ELN flexibility while keeping the core runtime portable.

### Checklist
- [ ] Define and document sync adapter port contract.
- [ ] Move Kadi sync behind adapter implementation boundary.
- [ ] Make Kadi adapter optional in dependency/packaging flow.
- [ ] Add adapter selection mechanism to startup config.
- [ ] Add startup test without Kadi adapter installed.
- [ ] Add startup test with Kadi adapter selected.
- [ ] Add startup test for clear error path when adapter name is unknown.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 4 Configuration Consolidation
- Why this matters: Multiple configuration sources create drift and make behavior hard to reason about across environments.

### Checklist
- [ ] Inventory all runtime reads from legacy constants.
- [ ] Move operational configuration reads to config schema/service path.
- [ ] Remove fallback usage from operational code paths.
- [ ] Add test for default config behavior.
- [ ] Add test for explicit path override behavior.
- [ ] Add test for environment-driven bootstrap behavior.
- [ ] Update docs with the canonical configuration flow.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 5 Processing Pipeline Decomposition
- Why this matters: Smaller focused services improve maintainability, test isolation, and future plugin onboarding.

### Checklist
- [ ] Define stage service boundaries (resolve, stabilize, preprocess, route, persist/sync).
- [ ] Extract one stage at a time with unit tests per stage.
- [ ] Keep integration behavior stable while orchestration is split.
- [ ] Reduce direct cross-module coupling in orchestration module.
- [ ] Validate no regressions in multi-device and multi-processor integration tests.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 6 Plugin and Discovery Hardening
- Why this matters: Plugin reliability is central to the architecture and required for open-source trust and extensibility.

### Checklist
- [ ] Normalize plugin package hygiene (`__init__.py` naming and structure).
- [ ] Remove stale plugin directories/artifacts not representing valid source plugins.
- [ ] Reconcile plugin inventory with optional dependency groups.
- [ ] Validate plugin discovery errors and messages are actionable.
- [ ] Update or remove outdated mapping expectations in tests.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 7 Desktop Runtime Integration
- Why this matters: Desktop support should sit on top of a stable headless core to avoid reintroducing tight coupling.

### Checklist
- [ ] Keep runtime mode selection explicit in composition root.
- [ ] Ensure headless mode remains green after desktop wiring changes.
- [ ] Ensure desktop mode preserves current UI interaction behavior.
- [ ] Add/refresh smoke tests for both runtime modes.
- [ ] Document runtime mode selection and behavior differences.

### Completion Notes
- How it was done: Pending.

---

## Section: Phase 8 Final Cutover and Cleanup
- Why this matters: A clean cutover prevents long-lived dual architecture and reduces maintenance cost.

### Checklist
- [ ] Switch canonical project/package identity to `dpost` in packaging and entrypoints.
- [ ] Update docs and scripts to new canonical names.
- [ ] Remove deprecated compatibility paths after validation window.
- [ ] Execute full lint and test suite as release gate.
- [ ] Prepare migration notes for contributors and users.

### Completion Notes
- How it was done: Pending.

---

## Section: Manual Check
- Why this matters: Human verification confirms real operator workflows beyond automated test coverage.

### Checklist
- [ ] Desktop manual check: app starts cleanly.
- [ ] Desktop manual check: file appears in watch directory and is processed.
- [ ] Desktop manual check: rename prompt appears for invalid prefix and cancellation routes to rename bucket.
- [ ] Desktop manual check: sync errors surface clear user-facing messages.
- [ ] Headless manual check: startup succeeds with no UI dependencies.
- [ ] Headless manual check: processing and sync still execute for representative test files.
- [ ] Headless manual check: observability and metrics endpoints start and respond.
- [ ] Plugin manual check: at least one plugin per instrument family loads and processes representative input.
- [ ] Plugin manual check: invalid plugin name produces actionable error message.
- [ ] Migration hygiene manual check: old and new entrypoints match behavior during transition window.
- [ ] Migration hygiene manual check: documented commands and setup instructions work on a clean environment.

### Completion Notes
- How it was done: Pending.
