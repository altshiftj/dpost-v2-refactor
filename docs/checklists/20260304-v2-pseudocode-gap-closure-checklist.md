# Checklist: V2 Pseudocode Traceability Gap Closure

## Objective
- Close all currently open pseudocode implementation traceability gaps with lane-owned, deterministic acceptance checks.

## Source of Truth
- `docs/reports/20260304-v2-pseudocode-implementation-traceability-matrix.csv`
- `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`

## Section: Critical Missing Modules
- Why this matters: missing modules block pseudocode-to-runtime realization and create hard parity risk.

### Checklist
- [ ] `Startup-Core`: implement `src/dpost_v2/__main__.py` for pseudocode id `__main__.py`.
- [ ] `Startup-Core`: add direct tests importing `dpost_v2.__main__`.
- [ ] `Records-Core`: implement `src/dpost_v2/application/records/service.py` for pseudocode id `application/records/service.py`.
- [ ] `Records-Core`: add direct tests importing `dpost_v2.application.records.service`.

### Manual Check
- [ ] Matrix row `__main__.py` shows:
  - `implementation_status=implemented`
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`
- [ ] Matrix row `application/records/service.py` shows:
  - `implementation_status=implemented`
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`

### Completion Notes
- How it was done: <fill after implementation lanes land and matrix is refreshed>

---

## Section: Direct Test Traceability Gaps
- Why this matters: modules without direct test imports can regress silently even when indirectly exercised.

### Checklist
- [ ] `Plugin-Host`: add direct tests importing `dpost_v2.plugins.contracts`.
- [ ] `Plugin-Device`: add direct tests importing `dpost_v2.plugins.devices._device_template.processor`.

### Manual Check
- [ ] Matrix row `plugins/contracts.py` shows:
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`
  - `direct_test_count >= 1`
- [ ] Matrix row `plugins/devices/_device_template/processor.py` shows:
  - `test_traceability_status=direct_module_tests_present`
  - `gap_severity=covered`
  - `direct_test_count >= 1`

### Completion Notes
- How it was done: <fill after plugin lanes land and matrix is refreshed>

---

## Section: Lane Gate
- Why this matters: keeps traceability closure verifiable and prevents stale gap reporting.

### Checklist
- [ ] Refresh matrix using `docs/checklists/20260304-v2-pseudocode-traceability-refresh-checklist.md`.
- [ ] Refresh summary report counts and gap register.
- [ ] Confirm this checklist has no open items before closing `docs-pseudocode-traceability` for this snapshot.

### Completion Notes
- How it was done: <fill after all gap rows are `gap_severity=covered`>
