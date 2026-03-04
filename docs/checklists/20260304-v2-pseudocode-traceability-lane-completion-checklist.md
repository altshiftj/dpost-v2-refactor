# Checklist: V2 Pseudocode Traceability Lane Completion

## Section: Deterministic Mapping
- Why this matters: traceability needs a repeatable rule set so parallel lanes do not drift when code lands.

### Checklist
- [x] Build matrix input from all non-README pseudocode specs with frontmatter `id`.
- [x] Map each `id` to `src/dpost_v2/<id>` using file-existence checks only.
- [x] Map each `id` to test traceability using direct imports in `tests/dpost_v2/**/test_*.py`.
- [x] Write full per-spec output to `docs/reports/20260304-v2-pseudocode-implementation-traceability-matrix.csv`.

### Completion Notes
- How it was done: produced a deterministic CSV matrix with one row per pseudocode spec, including implementation state, test traceability state, and direct test file links.

---

## Section: Gap Reconciliation
- Why this matters: unresolved pseudocode-to-code gaps are the highest risk for migration drift.

### Checklist
- [x] Enumerate missing implementation targets from pseudocode ids.
- [x] Enumerate implemented modules that currently lack direct module test imports.
- [x] Record gap details in `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`.

### Manual Check
- [x] Open matrix row for `docs/pseudocode/__main__.md` and verify `missing_implementation`.
- [x] Open matrix row for `docs/pseudocode/application/records/service.md` and verify `missing_implementation`.
- [x] Open matrix rows for plugin contracts and device template processor and verify `no_direct_module_test_import`.

### Completion Notes
- How it was done: gap register was derived directly from matrix statuses and copied without manual reclassification.

---

## Section: Publication and Baseline Pointer
- Why this matters: future lanes need a single current traceability baseline to keep status updates consistent.

### Checklist
- [x] Publish summary report in `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`.
- [x] Update `docs/pseudocode/README.md` active baseline to include traceability report + matrix pointers.
- [x] Publish recurring refresh runbook in `docs/checklists/20260304-v2-pseudocode-traceability-refresh-checklist.md`.
- [x] Keep lane scope docs-only (no `src/` or `tests/` edits).

### Completion Notes
- How it was done: published report + matrix and updated pseudocode README baseline links; no runtime or test code files were modified.
