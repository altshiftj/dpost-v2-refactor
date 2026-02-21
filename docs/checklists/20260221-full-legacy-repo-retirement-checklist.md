# Full Legacy Repo Retirement Checklist

## Section: Baseline and Governance Freeze
- Why this matters: Retirement without a locked baseline risks deleting
  capabilities that are still operationally required.

### Checklist
- [x] Capture legacy repository inventory and reference counts.
- [x] Define retirement target end-state criteria.
- [x] Add migration guard tests for repository-wide retirement criteria.
- [x] Link roadmap/checklist/report artifacts from active contributor docs.
- [ ] Define explicit exception policy for any temporary retained legacy files.

### Completion Notes
- How it was done: Inventory baseline captured in
  `docs/reports/20260221-full-legacy-repo-retirement-inventory.md`.
  Migration guard coverage started in
  `tests/migration/test_full_legacy_repo_retirement_harness.py` with explicit
  assertions for shared helper decoupling from legacy interaction/sync imports.
  Roadmap/checklist/report artifacts are linked from canonical contributor docs
  (`README.md`, `DEVELOPER_README.md`).

---

## Section: Test Harness Canonicalization
- Why this matters: Legacy tests are the largest remaining coupling surface and
  must migrate before safe source deletion.

### Checklist
- [ ] Migrate shared fixtures in `tests/conftest.py` and `tests/helpers/**` to
      canonical dpost imports.
- [ ] Remove `ipat_watchdog` imports from migration tests.
- [ ] Remove `ipat_watchdog` imports from unit tests.
- [ ] Remove `ipat_watchdog` imports from integration tests.
- [ ] Remove `ipat_watchdog` imports from manual tests.
- [ ] Keep migration/full gates green during each test migration slice.

### Completion Notes
- How it was done: In progress. Shared helper interfaces were migrated from
  legacy imports in:
  - `tests/helpers/fake_ui.py`
  - `tests/helpers/fake_sync.py`
  Conftest and remaining helper modules still require follow-up migration
  slices.

---

## Section: Plugin Package Retirement
- Why this matters: Full retirement requires eliminating duplicated plugin
  trees and converging tests/imports on canonical dpost plugins.

### Checklist
- [ ] Confirm all plugin loaders/tests resolve canonical dpost plugin paths.
- [ ] Retire `src/ipat_watchdog/device_plugins/**` in bounded slices.
- [ ] Retire `src/ipat_watchdog/pc_plugins/**` in bounded slices.
- [ ] Remove stale legacy plugin-specific docs and naming references.
- [ ] Verify plugin loading/actionability parity after each slice.

### Completion Notes
- How it was done: Pending.

---

## Section: Core Package Retirement
- Why this matters: Legacy core module deletion is the decisive step to remove
  dual-architecture maintenance burden.

### Checklist
- [ ] Retire `src/ipat_watchdog/core/app/**` after canonical test migration.
- [ ] Retire `src/ipat_watchdog/core/processing/**` after parity tests remain green.
- [ ] Retire `src/ipat_watchdog/core/records/**` and `core/sync/**` after parity checks.
- [ ] Retire `src/ipat_watchdog/core/config/**`, `core/storage/**`, and `core/ui/**`.
- [ ] Remove residual legacy package exports and dead imports.

### Completion Notes
- How it was done: Pending.

---

## Section: Packaging and Documentation Finalization
- Why this matters: Packaging/docs must match the real architecture so
  contributors and users do not follow stale legacy paths.

### Checklist
- [ ] Remove legacy package metadata/entrypoint references from `pyproject.toml`.
- [ ] Ensure README/USER/DEVELOPER docs are canonical-dpost only.
- [ ] Update architecture baseline/contract/responsibility and ADR trail.
- [ ] Update `GLOSSARY.csv` for retirement terminology changes.
- [ ] Capture final retirement closure report with exact gate evidence.

### Completion Notes
- How it was done: Pending.

---

## Section: Manual Check
- Why this matters: Human workflow checks validate operator-facing behavior
  that can still regress despite broad automated coverage.

### Checklist
- [ ] Desktop runtime manual check after legacy package deletion.
- [ ] Headless runtime manual check after legacy package deletion.
- [ ] Plugin family spot checks across representative instruments.
- [ ] Records/sync side-effect check with a failing-sync scenario.
- [ ] Contributor usability check: docs are sufficient without legacy tracing.

### Manual Validation Steps
1. Run `python -m dpost` in `desktop` mode and process valid/invalid files.
2. Run `python -m dpost` in `headless` mode and verify processing + endpoints.
3. Execute representative plugin workloads and one unknown-plugin failure path.
4. Validate local record persistence and sync retry/error behavior.
5. Perform a cold-read of contributor docs and extension contracts.

### Completion Notes
- How it was done: Pending.
