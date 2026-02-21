# Part 3 Domain Layer Extraction Checklist

## Section: Domain Foundation
- Why this matters: A stable domain package layout prevents ad-hoc moves and
  dependency cycles later in the extraction.

### Checklist
- [x] Create domain subpackage structure for processing ownership.
- [x] Expand domain subpackage structure for records ownership.
- [x] Add initial domain characterization tests before moving implementations.
- [x] Define explicit import rules for domain/application/infrastructure usage.

### Completion Notes
- How it was done: Added `src/dpost/domain/processing/` modules and Part 3
  migration ownership tests to lock extraction boundaries before broader moves,
  then added `src/dpost/domain/records/` for entity ownership.

---

## Section: Routing and Value Model Extraction
- Why this matters: Routing decisions and value models are high-leverage
  business rules that should not depend on infrastructure code.

### Checklist
- [x] Move processing enums/dataclasses from application to domain modules.
- [x] Extract pure routing decision policy into domain helper(s).
- [x] Keep application orchestration focused on lookups, side effects, and
      workflow sequencing.
- [x] Update tests for moved imports and behavioral parity.

### Completion Notes
- How it was done: Retired
  `src/dpost/application/processing/models.py`, moved value models to
  `src/dpost/domain/processing/models.py`, moved routing policy to
  `src/dpost/domain/processing/routing.py`, and rewired application/test imports.

---

## Section: Record Entity Extraction
- Why this matters: Record lifecycle rules are core domain behavior and should
  remain testable without runtime/global state dependencies.

### Checklist
- [x] Move `LocalRecord` into domain ownership.
- [x] Remove runtime-config accessor coupling from record entity behavior.
- [x] Keep persistence and sync triggers in application record manager.
- [x] Verify record serialization and sync-state transitions remain unchanged.

### Completion Notes
- How it was done: Moved entity to
  `src/dpost/domain/records/local_record.py`, removed direct
  `application.config.current()` accessor dependency, updated record loading
  to pass separator explicitly at infrastructure boundary, and validated parity
  via record/session/sync/unit + migration suites.

---

## Section: Batch and Staging Policy Extraction
- Why this matters: Batch aggregation and pair reconstruction are domain
  policies that should be reusable across processors without orchestration
  coupling.

### Checklist
- [x] Move pure batch model/value types to domain processing modules.
- [x] Move pure staging pair-reconstruction policy to domain modules.
- [x] Keep filesystem mutation and logging concerns outside domain.
- [x] Verify plugin processor tests stay green after policy moves.

### Completion Notes
- How it was done: Moved shared batch value models to
  `src/dpost/domain/processing/batch_models.py`, moved pair reconstruction and
  stale-stage policies to `src/dpost/domain/processing/staging.py`, rewired
  PSA/Kinexus processors to consume domain modules, moved shared text decode
  policy to `src/dpost/domain/processing/text.py`, rewired PSA/Kinexus/DSV to
  consume the domain helper, and kept stage-dir creation in application helpers.

---

## Section: Contract Cleanup and Governance
- Why this matters: Domain extraction is incomplete until old ownership paths
  are removed and governance docs reflect actual architecture.

### Checklist
- [x] Remove superseded application-local model/policy duplicates.
- [x] Update architecture baseline/contract/responsibility docs.
- [x] Record major extraction decisions in ADRs as needed.
- [x] Capture checkpoint evidence in roadmap/report artifacts.

### Completion Notes
- How it was done: Retired application-local processing model and batch model
  modules, updated responsibility catalog ownership rows, and refreshed Part 3
  roadmap/report progress snapshots, including
  `ADR-0005-domain-processing-and-record-ownership-extraction.md`; followed by
  domain purity hardening (`test_part3_domain_purity_boundaries.py`) to remove
  residual domain imports of application/infrastructure modules; then extracted
  filename-prefix policy ownership to
  `src/dpost/domain/naming/prefix_policy.py` with config-aware application
  facade `src/dpost/application/naming/policy.py` and ownership guard
  `tests/migration/test_part3_domain_naming_policy_ownership.py`; then
  extracted filename parsing and record/file identifier policy to
  `src/dpost/domain/naming/identifiers.py`, rewired processing/records flows
  to app naming facade helpers, and added guard
  `tests/migration/test_part3_domain_naming_identifier_ownership.py`; then
  moved filesystem stage-dir helper ownership to
  `src/dpost/infrastructure/storage/staging_dirs.py`, retired
  `src/dpost/application/processing/staging_utils.py`, and tightened staging
  ownership guard expectations in
  `tests/migration/test_part3_domain_batch_staging_ownership.py`; then removed
  stale legacy wording from canonical runtime sources and added wording guard
  `tests/migration/test_part3_canonical_wording_cleanup.py`; then retired
  `_ProcessingPipeline._route_with_prefix()` and updated stage-boundary
  migration tests to assert direct rename-flow seam behavior.

---

## Section: Manual Check
- Why this matters: Manual workflows confirm no operator-facing regressions
  after structural extraction work.

### Checklist
- [x] Desktop mode workflow check after domain extraction waves.
- [x] Headless mode workflow check after domain extraction waves.
- [x] Representative plugin processing spot check across at least 3 device
      families.
- [x] Sync failure/retry workflow verification with persisted records.
- [x] Contributor cold-read validation of updated architecture docs.

### Manual Validation Steps
1. Run `python -m dpost` with desktop runtime and process valid + invalid files.
2. Run `python -m dpost` with headless runtime and verify processing plus
   observability endpoints.
3. Execute representative plugins (including one staged/batch processor) and
   validate produced record paths/files.
4. Force one sync failure path and verify retry/error behavior and persistence.
5. Read architecture docs end-to-end and confirm domain ownership is clear
   without tracing application internals.

### Completion Notes
- How it was done: Human operator reported manual validation complete on
  2026-02-21 using the consolidated runbook steps captured in:
  `docs/checklists/20260221-final-manual-validation-runbook.md`.
