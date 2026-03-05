# Checklist: V2 Pseudocode Population (Autonomous Night Run)

## Objective
- Fill `docs/pseudocode/**` files that are still placeholders so each file has concrete intent, mappings, and executable pseudocode before V2 coding begins.

## Reference Set (Required)
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`
- `docs/pseudocode/README.md`
- `docs/` architecture and planning docs for traceability links.

## Section: Runbook Preparation
- Why this matters: Without a frozen reference set and execution order, file-level population drifts and becomes inconsistent across lanes.

### Checklist
- [x] Create a one-pass inventory of `docs/pseudocode` markdown files and tag each as `pending`, `in-progress`, or `done`.
- [x] Add `origin` mappings for each pending file from `20260303-v1-to-v2-exhaustive-file-mapping-rpc.md` (if no direct V1 match, mark as design-target only).
- [x] Add a short `v2-improvement-intent` note to each file describing why this file exists in the clean-room rewrite.
- [x] Agree a single pass order: `contracts -> domain -> startup -> runtime -> ingestion -> records/session -> infrastructure -> plugins -> review`.
- [x] Freeze that order in `docs/checklists/20260304-v2-pseudocode-population-checklist.md`.

### Completion Notes
- How it was done: inventoried 65 non-README specs, preserved/validated origin mappings and V2 improvement intent sections, and executed a frozen lane order with section checkpoint commits.

---

## Section: Contracts Lane
- Why this matters: Contracts are the dependency boundary. They must be accurate before any lane writes code or pseudocode that depends on them.

### Checklist
- [x] `docs/pseudocode/application/contracts/context.md`: replace placeholders with `RuntimeContext`, `ProcessingContext`, constructors, and invariants.
- [x] `docs/pseudocode/application/contracts/events.md`: replace placeholders with event taxonomy and event payload contract.
- [x] `docs/pseudocode/application/contracts/plugin_contracts.md`: replace placeholders with plugin contract shape and capability semantics.
- [x] `docs/pseudocode/application/contracts/ports.md`: replace placeholders with port matrix and failure behavior.

### Manual Check
- [x] One-liner sanity check: every contract file has no `TBD` text.
- [x] Verify each contract doc includes explicit import/return types and at least one failure mode.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/application/contracts`.

### Completion Notes
- How it was done: populated all four contract specs with concrete models/protocols, deterministic validation rules, and explicit failure/error taxonomies; verified `rg "TBD" docs/pseudocode/application/contracts` returns no matches.

---

## Section: Runtime Entry and Startup
- Why this matters: entrypoint and startup docs define how V2 boots; ambiguities here propagate into all slices.

### Checklist
- [x] `docs/pseudocode/__main__.md`: replace placeholders with arg parsing, mode dispatch, and safe defaulting behavior.
- [x] `docs/pseudocode/application/startup/context.md`: replace placeholders with explicit context builder and startup lifecycle state.
- [x] `docs/pseudocode/application/startup/settings.md`: replace placeholders with naming, profile, and mode settings intent.
- [x] `docs/pseudocode/application/startup/settings_schema.md`: replace placeholders with schema rules and validation errors.
- [x] `docs/pseudocode/application/startup/settings_service.md`: replace placeholders with load/merge/normalize policy and cache behavior.
- [x] `docs/pseudocode/application/startup/bootstrap.md`: replace placeholders with startup sequence and failure boundaries.
- [x] `docs/pseudocode/runtime/composition.md`: replace placeholders with composition root wiring and ownership boundaries.
- [x] `docs/pseudocode/runtime/startup_dependencies.md`: replace placeholders with dependency graph and lazy vs eager loading policy.

### Manual Check
- [x] Confirm `docs/pseudocode/application/startup` and `docs/pseudocode/runtime` are internally aligned: startup docs reference composition/runtime docs and vice versa.
- [x] Ensure every startup doc has at least one explicit startup failure mode.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/application/startup docs/pseudocode/runtime docs/pseudocode/__main__.md`.

### Completion Notes
- How it was done: populated entrypoint/startup/runtime composition specs with explicit boot order, validation boundaries, dependency selection, and typed startup failures; verified no `TBD` remains in startup/runtime scopes.

---

## Section: Application Runtime and Session
- Why this matters: session boundaries and orchestration define the production behavior envelope; these should be explicit before implementation starts.

### Checklist
- [x] `docs/pseudocode/application/runtime/dpost_app.md`: replace placeholders with event loop, retry cadence, and stage handoff behavior.
- [x] `docs/pseudocode/application/session/session_manager.md`: replace placeholders with timeout, transitions, and abort semantics.
- [x] `docs/pseudocode/application/records/service.md`: replace placeholders with `create`, `update`, `mark_unsynced`, `save` lifecycle contract.

### Manual Check
- [x] Confirm `application/runtime` references `application/contracts` and not implementation internals.
- [x] Confirm each file has at least one explicit idempotency condition.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/application/runtime docs/pseudocode/application/session docs/pseudocode/application/records/service.md`.

### Completion Notes
- How it was done: populated runtime orchestration, session lifecycle, and records service docs with deterministic transitions, explicit idempotency conditions, and normalized failure outcomes; verified lane grep has no `TBD`.

---

## Section: Ingestion Pipeline Core
- Why this matters: this is the functional heart of V2 and has the highest parity risk.

### Checklist
- [x] `docs/pseudocode/application/ingestion/engine.md`: replace placeholders with high-level pipeline execution flow and halt semantics.
- [x] `docs/pseudocode/application/ingestion/processor_factory.md`: replace placeholders with plugin selection, caching, and fallback policy.
- [x] `docs/pseudocode/application/ingestion/runtime_services.md`: replace placeholders with runtime side-effect boundary and ownership matrix.
- [x] `docs/pseudocode/application/ingestion/models/candidate.md`: replace placeholders with candidate creation, validation, and immutable constraints.
- [x] `docs/pseudocode/application/ingestion/stages/pipeline.md`: replace placeholders with stage graph transitions and result propagation.
- [x] `docs/pseudocode/application/ingestion/stages/resolve.md`: replace placeholders with plugin resolution and device lookup semantics.
- [x] `docs/pseudocode/application/ingestion/stages/stabilize.md`: replace placeholders with debounce and settle-time behavior.
- [x] `docs/pseudocode/application/ingestion/stages/route.md`: replace placeholders with deterministic route decision and naming policy integration.
- [x] `docs/pseudocode/application/ingestion/stages/persist.md`: replace placeholders with persist/rename/reject control flow and outcomes.
- [x] `docs/pseudocode/application/ingestion/stages/post_persist.md`: replace placeholders with post-persist hooks and sync triggers.
- [x] `docs/pseudocode/application/ingestion/policies/error_handling.md`: replace placeholders with normalized severity mapping and conversion policy.
- [x] `docs/pseudocode/application/ingestion/policies/failure_outcome.md`: replace placeholders with failure taxonomy and state transitions.
- [x] `docs/pseudocode/application/ingestion/policies/failure_emitter.md`: replace placeholders with emission channel and formatting rules.
- [x] `docs/pseudocode/application/ingestion/policies/modified_event_gate.md`: replace placeholders with dedupe strategy and time-window behavior.
- [x] `docs/pseudocode/application/ingestion/policies/immediate_sync_error_emitter.md`: replace placeholders with immediate-sync error escalation policy.
- [x] `docs/pseudocode/application/ingestion/policies/force_path.md`: replace placeholders with force-path override and safety checks.
- [x] `docs/pseudocode/application/ingestion/policies/retry_planner.md`: replace placeholders with retry windows, caps, and jitter strategy.

### Manual Check
- [x] Map every stage/policy file to the equivalent V1 files in the v1-to-v2 exhaustive mapping.
- [x] Validate stage contracts are acyclic and every stage has one explicit terminal result type.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/application/ingestion`.

### Completion Notes
- How it was done: populated all ingestion engine/model/stage/policy docs with deterministic stage flow, typed terminal outcomes, retry/failure normalization, and side-effect boundary semantics; verified `rg "TBD" docs/pseudocode/application/ingestion` returns no matches.

---

## Section: Domain Layer
- Why this matters: domain files should encode pure business rules that can be ported with high-confidence tests.

### Checklist
- [x] `docs/pseudocode/domain/naming/identifiers.md`: replace placeholders with parse/compose rules and edge-case handling.
- [x] `docs/pseudocode/domain/naming/prefix_policy.md`: replace placeholders with prefix derivation and fallback behavior.
- [x] `docs/pseudocode/domain/naming/policy.md`: replace placeholders with canonical naming policy + separator integration.
- [x] `docs/pseudocode/domain/routing/rules.md`: replace placeholders with deterministic route rules and precedence handling.
- [x] `docs/pseudocode/domain/processing/models.md`: replace placeholders with processing outcome models and invariants.
- [x] `docs/pseudocode/domain/processing/batch_models.md`: replace placeholders with batch semantics and partitioning behavior.
- [x] `docs/pseudocode/domain/processing/staging.md`: replace placeholders with staging-state transitions and invariants.
- [x] `docs/pseudocode/domain/processing/text.md`: replace placeholders with text extraction and normalization rules.
- [x] `docs/pseudocode/domain/records/local_record.md`: replace placeholders with record entity integrity and lifecycle boundaries.

### Manual Check
- [x] Verify domain docs do not mention concrete I/O APIs or adapters.
- [x] Verify all domain docs include at least one example of invariant enforcement and one counterexample.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/domain`.

### Completion Notes
- How it was done: populated all domain naming/routing/processing/record docs with pure-rule behavior, explicit invariant examples and counterexamples, and typed domain failures; verified `rg "TBD" docs/pseudocode/domain` returns no matches.

---

## Section: Infrastructure Layer
- Why this matters: infra files define integration behavior and must explicitly separate adapter behavior from domain logic.

### Checklist
- [x] `docs/pseudocode/infrastructure/storage/file_ops.md`: replace placeholders with explicit file operation contract and error taxonomy.
- [x] `docs/pseudocode/infrastructure/storage/record_store.md`: replace placeholders with persistence model, transaction behavior, and migration notes.
- [x] `docs/pseudocode/infrastructure/storage/staging_dirs.md`: replace placeholders with directory derivation and cleanup policy.
- [x] `docs/pseudocode/infrastructure/sync/noop.md`: replace placeholders with no-op mode semantics and traceability behavior.
- [x] `docs/pseudocode/infrastructure/sync/kadi.md`: replace placeholders with sync contract mapping and conflict handling.
- [x] `docs/pseudocode/infrastructure/observability/logging.md`: replace placeholders with structured logging boundaries.
- [x] `docs/pseudocode/infrastructure/observability/metrics.md`: replace placeholders with metric dimensions and cardinality controls.
- [x] `docs/pseudocode/infrastructure/observability/tracing.md`: replace placeholders with correlation ID and stage span behavior.
- [x] `docs/pseudocode/infrastructure/runtime/ui/factory.md`: replace placeholders with adapter selection strategy.
- [x] `docs/pseudocode/infrastructure/runtime/ui/adapters.md`: replace placeholders with adapter contracts and capability matrix.
- [x] `docs/pseudocode/infrastructure/runtime/ui/headless.md`: replace placeholders with headless lifecycle and deterministic outputs.
- [x] `docs/pseudocode/infrastructure/runtime/ui/tkinter.md`: replace placeholders with desktop-only behavior and fallback conditions.
- [x] `docs/pseudocode/infrastructure/runtime/ui/desktop.md`: replace placeholders with desktop orchestration details.
- [x] `docs/pseudocode/infrastructure/runtime/ui/dialogs.md`: replace placeholders with prompt patterns and non-blocking concerns.

### Manual Check
- [x] Confirm all infrastructure pseudocode files include `Inputs`, `Outputs`, and `Failure Modes`.
- [x] Confirm no cross-layer imports are implied except through application contracts.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/infrastructure`.

### Completion Notes
- How it was done: populated storage/sync/observability/UI adapter specs with explicit side-effect ownership, typed adapter error taxonomy, and contract-bound inputs/outputs; verified `rg "TBD" docs/pseudocode/infrastructure` returns no matches.

---

## Section: Plugins
- Why this matters: plugin contracts are a hot integration lane and need stable pseudocode to support parallel implementation.

### Checklist
- [x] `docs/pseudocode/plugins/host.md`: replace placeholders with plugin lifecycle, registration, and capability arbitration.
- [x] `docs/pseudocode/plugins/discovery.md`: replace placeholders with discovery mechanism and deterministic plugin loading.
- [x] `docs/pseudocode/plugins/catalog.md`: replace placeholders with catalog semantics and versioned metadata policy.
- [x] `docs/pseudocode/plugins/contracts.md`: replace placeholders with public plugin API contract and expectations.
- [x] `docs/pseudocode/plugins/profile_selection.md`: replace placeholders with profile-to-plugin selection strategy.
- [x] `docs/pseudocode/plugins/devices/_device_template/plugin.md`: replace placeholders with plugin implementation template and required exports.
- [x] `docs/pseudocode/plugins/devices/_device_template/processor.md`: replace placeholders with processor behavior contract and preprocessing model.
- [x] `docs/pseudocode/plugins/devices/_device_template/settings.md`: replace placeholders with settings schema and defaults.
- [x] `docs/pseudocode/plugins/pcs/_pc_template/plugin.md`: replace placeholders with PC plugin contract and sync lifecycle hooks.
- [x] `docs/pseudocode/plugins/pcs/_pc_template/settings.md`: replace placeholders with PC profile and sync settings schema.

### Manual Check
- [x] Ensure each plugin template has explicit required entry points: init metadata, process/prepare methods, and capability flags.
- [x] Ensure templates map to real V1 plugin directories in the mapping document.
- [x] Run a grep audit: `rg "TBD" docs/pseudocode/plugins`.

### Completion Notes
- How it was done: populated plugin host/discovery/catalog/contracts/profile specs and device/pc templates with deterministic selection/lifecycle behavior and explicit required entry points (`metadata`, `capabilities`, processor/sync factories); verified `rg "TBD" docs/pseudocode/plugins` returns no matches.

---

## Section: Cross-Lane Validation
- Why this matters: even if each doc is individually populated, cross-lane coherence is the main failure mode before V2 coding starts.

### Checklist
- [x] For every `docs/pseudocode` file with `id` frontmatter, ensure `id` path matches the documented target V2 path.
- [x] For every populated file, add/update `origin`/`source` references to mapped V1 files.
- [x] For every populated file, add at least one "Tests To Implement" entry with explicit unit/integration intent.
- [x] Add/refresh top-level `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md` pointers to this checklist as the active population baseline.
- [x] Add/refresh `docs/pseudocode/README.md` if needed with checklist execution order and completion status.

### Manual Check
- [x] `rg "TBD" docs/pseudocode` returns zero matches after completion.
- [x] `rg "origin|source|v1" docs/pseudocode -n` should show at least one origin reference in each previously-placeholder file.
- [x] Confirm the mapping artifact still reflects the same target files (quick diff spot-check for `__main__`, `runtime`, `contracts`, and three plugin files).

### Completion Notes
- How it was done: ran global placeholder/origin audits, validated `id` path alignment for all 65 specs, refreshed blueprint + pseudocode README pointers, and spot-checked mapping entries for startup/runtime/contracts/plugins targets.

---

## Section: Gate and Handoff
- Why this matters: this keeps the overnight run actionable and resumable by the next model.

### Checklist
- [x] Generate final status matrix: `pending | done` per file.
- [x] Add completion summary in `docs/reports/` (or equivalent) with parity-risk assessment for pseudocode completeness.
- [x] Save and stage all changes with a commit titled `docs: populate v2 pseudocode coverage map`.
- [x] Include a short handoff message in the final run notes with remaining gaps only.

### Manual Check
- [x] Verify all modified files are in the intended scope (`docs/pseudocode`, checklist/report documents, required planning baseline pointer update, and glossary synchronization in `GLOSSARY.csv`).
- [x] Confirm no code under `src/` was edited in this pass unless explicitly requested.

### Completion Notes
- How it was done: generated per-file completion matrix + parity-risk report in `docs/reports/20260304-v2-pseudocode-population-report.md`, synchronized new cross-cutting terms in `GLOSSARY.csv`, and committed final coverage-map checkpoint with required title.

