# Checklist: V2 Pseudocode Traceability Gap Closure

## Objective
- Close all currently open pseudocode implementation traceability gaps with lane-owned, deterministic acceptance checks.

## Source of Truth
- `docs/reports/20260304-v2-pseudocode-implementation-traceability-matrix.csv`
- `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`

## Section: Critical Missing Modules
- Why this matters: missing modules block pseudocode-to-runtime realization and create hard parity risk.

### Checklist
- [x] `Startup-Core`: implement `src/dpost_v2/__main__.py` for pseudocode id `__main__.py`.
- [x] `Startup-Core`: add direct tests importing `dpost_v2.__main__`.
- [x] `Records-Core`: implement `src/dpost_v2/application/records/service.py` for pseudocode id `application/records/service.py`.
- [x] `Records-Core`: add direct tests importing `dpost_v2.application.records.service`.

### Manual Check
- [x] Matrix row `__main__.py` shows:
  - `implementation_status=implemented`
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`
- [x] Matrix row `application/records/service.py` shows:
  - `implementation_status=implemented`
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`

### Completion Notes
- How it was done: Added `src/dpost_v2/__main__.py` plus `tests/dpost_v2/test___main__.py`, and added `src/dpost_v2/application/records/service.py` plus `tests/dpost_v2/application/records/test_service.py`; then refreshed the matrix.

---

## Section: Direct Test Traceability Gaps
- Why this matters: modules without direct test imports can regress silently even when indirectly exercised.

### Checklist
- [x] `Plugin-Host`: add direct tests importing `dpost_v2.plugins.contracts`.
- [x] `Plugin-Device`: add direct tests importing `dpost_v2.plugins.devices._device_template.processor`.

### Manual Check
- [x] Matrix row `plugins/contracts.py` shows:
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`
  - `direct_test_count >= 1`
- [x] Matrix row `plugins/devices/_device_template/processor.py` shows:
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`
  - `direct_test_count >= 1`

### Completion Notes
- How it was done: Added `tests/dpost_v2/plugins/test_direct_module_imports.py` with explicit direct module imports for both targets and refreshed the matrix.

---

## Section: Lane Gate
- Why this matters: keeps traceability closure verifiable and prevents stale gap reporting.

### Checklist
- [x] Refresh matrix using `docs/checklists/20260304-v2-pseudocode-traceability-refresh-checklist.md`.
- [x] Refresh summary report counts and gap register.
- [x] Confirm this checklist has no open items before closing `docs-pseudocode-traceability` for this snapshot.

### Completion Notes
- How it was done: Recomputed the matrix using deterministic path/import rules, updated the report snapshot counts, and confirmed no rows remain in `critical_missing_module` or `test_traceability_gap`.
