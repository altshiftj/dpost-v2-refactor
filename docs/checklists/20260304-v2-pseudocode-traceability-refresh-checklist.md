# Checklist: V2 Pseudocode Traceability Refresh

## Objective
- Keep pseudocode-to-implementation and pseudocode-to-tests mapping current after each V2 lane lands.

## Section: Regenerate Matrix
- Why this matters: stale mapping causes silent drift between pseudocode and merged code.

### Checklist
- [x] Recompute matrix rows for all non-README pseudocode specs with frontmatter `id`.
- [x] Recompute implementation status by checking existence of `src/dpost_v2/<id>`.
- [x] Recompute test traceability status by scanning direct imports in `tests/dpost_v2/**/test_*.py`.
- [x] Recompute lane ownership and severity fields (`lane`, `gap_severity`, `direct_test_count`).
- [x] Overwrite `docs/reports/20260304-v2-pseudocode-implementation-traceability-matrix.csv`.

### Manual Check
- [x] Matrix row count equals current pseudocode non-README spec count.
- [x] Matrix has only these status values:
  - `implemented`
  - `missing_implementation`
  - `direct_module_tests_present`
  - `no_direct_module_test_import`
  - `missing_tests`

### Completion Notes
- How it was done: recomputed deterministic matrix from pseudocode frontmatter (`id`, `lane`) and direct import scans in `tests/dpost_v2/**/test_*.py`; regenerated CSV output was byte-identical to the committed matrix (`65` rows, no row-level deltas).

---

## Section: Reconcile Gap Register
- Why this matters: unresolved gaps must stay explicit so implementation lanes can close them deterministically.

### Checklist
- [x] Update the gap register in `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`.
- [x] Keep ordering stable:
  - missing implementation and tests
  - implemented with no direct module test import
- [x] Update coverage snapshot counts and area breakdown counts in the same report.

### Manual Check
- [x] Every gap listed in the report is represented by at least one matrix row.
- [x] No matrix gap row is omitted from the report.

### Completion Notes
- How it was done: verified gap register against matrix statuses and kept severity ordering stable; no gap changes were detected and counts remained `63 implemented / 2 missing / 2 direct-test gaps`.

---

## Section: Publish Baseline Updates
- Why this matters: baseline pointers in planning docs must reflect the newest snapshot.

### Checklist
- [x] If counts changed, update snapshot counts in:
  - `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`
- [x] Ensure baseline links remain present in:
  - `docs/pseudocode/README.md`
  - `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- [x] Record a checkpoint commit with a docs-scoped message.

### Completion Notes
- How it was done: verified baseline pointers are present and valid in pseudocode and planning docs; counts were unchanged so the mapping RPC snapshot block required no edits, then recorded a docs-scoped checkpoint commit for the refresh.
