# Checklist: Legacy-Docs-Tooling Lane Completion

## Date
- 2026-03-05

## Scope
- Align docs and tooling with post-retirement V2-only architecture.
- Preserve `dpost` command name.
- Remove or archive-mark active references to legacy `src/dpost` runtime and legacy test lanes.

## Section: Top-Level Docs and Contributor Guidance
- Why this matters: contributors need one unambiguous active runtime/test surface.

### Checklist
- [x] Updated `README.md` to V2-only active paths and checks.
- [x] Updated `DEVELOPER_README.md` to V2 runtime/layout and plugin contracts.
- [x] Updated `CONTRIBUTING.md` quality gates to `src/dpost_v2` + `tests/dpost_v2`.
- [x] Updated `AGENTS.md` operating guidance for V2-only active scope.

### Manual Check
- [x] Confirm top-level docs no longer present legacy paths as active runtime targets.

### Completion Notes
- Active references now point to `src/dpost_v2/` and `tests/dpost_v2/`.

---

## Section: Architecture Documentation Alignment
- Why this matters: architecture/runbooks must match executable ownership boundaries.

### Checklist
- [x] Refreshed architecture baseline for current V2 runtime ownership.
- [x] Refreshed architecture contract and responsibility catalog to V2 modules.
- [x] Refreshed extension contracts for V2 plugin/sync boundaries.
- [x] Refreshed architecture overview narrative to V2 startup/composition flow.
- [x] Added archive status notes to historical ADRs that still reference legacy paths.

### Manual Check
- [x] Verify `docs/architecture/*.md` active guidance points to V2 module namespaces.

### Completion Notes
- Active architecture docs now describe `src/dpost_v2/**` as source of truth.

---

## Section: Planning/Pseudocode/Legacy Lane Prompt Hygiene
- Why this matters: historical artifacts can remain, but must be clearly marked archival.

### Checklist
- [x] Added archive-status callouts to migration-era planning docs that retain legacy mappings.
- [x] Added archive-status callouts to legacy cleanup lane prompts.
- [x] Converted `docs/pseudocode/README.md` to explicit archive-status guidance.
- [x] Updated one stale CI-alignment checklist note to remove obsolete nested legacy path wording.

### Manual Check
- [x] Confirm historical docs are clearly labeled and do not read as active runtime policy.

### Completion Notes
- Historical references retained for traceability and explicitly marked as archive context.

---

## Section: Tooling and Metadata Alignment
- Why this matters: packaging and test metadata must execute against V2 by default.

### Checklist
- [x] Updated `pyproject.toml` script entry to `dpost_v2.__main__:main`.
- [x] Kept command name `dpost`.
- [x] Updated pytest marker description to position `legacy` as archived-only.
- [x] Updated glossary terms/paths to V2 locations for active concepts.

### Manual Check
- [x] Verify `dpost` script target resolves to V2 entrypoint.

### Completion Notes
- Runtime command identity remains stable while execution target is V2.

---

## Section: Validation and Results
- Why this matters: docs/tooling updates should not regress active V2 quality gates.

### Checklist
- [x] Ran `python -m ruff check src/dpost_v2 tests/dpost_v2`.
- [x] Ran `python -m pytest -q tests/dpost_v2`.
- [x] Confirmed clean git status after checkpoint commit.

### Manual Check
- [x] `ruff` result: pass.
- [x] `pytest` result: `350 passed`.

### Completion Notes
- Validation succeeded with no active V2 test or lint regressions.

---

## Risks and Assumptions
- Runtime code still contains transitional mode tokens in `src/dpost_v2/__main__.py`; this lane treated runtime code edits as out of scope.
- Historical archive content may still contain legacy paths by design; these are now intentionally labeled archive context.

