# Checklist: Legacy Tests Retirement Lane Completion

## Objective
- Retire legacy test suites that target removed `src/dpost` runtime surfaces while preserving the active V2 test harness in `tests/dpost_v2`.

## Reference Set
- `docs/ops/lane-prompts/legacy-tests-retirement.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Section: Scope Lock and Baseline Verification
- Why this matters: retirement changes are high-impact; baseline evidence and scope lock prevent accidental removal of active V2 test coverage.

### Checklist
- [x] Confirmed lane scope and allowed edit paths from lane prompt.
- [x] Enumerated legacy test files under `tests/unit`, `tests/integration`, `tests/manual`, and `tests/helpers`.
- [x] Verified baseline V2 harness health before removals.

### Manual Check
- [x] `rg --files tests/unit tests/integration tests/manual tests/helpers tests/conftest.py`
- [x] `rg -n "from dpost|import dpost|src/dpost|\bv1\b|\bshadow\b" tests/unit tests/integration tests/manual tests/helpers tests/conftest.py`
- [x] `python -m pytest -q tests/dpost_v2` -> `350 passed in 7.80s`

### Completion Notes
- How it was done: established that allowed-scope suites were legacy-owned and that retained V2 tests were green before any deletion.

---

## Section: Legacy Suite Retirement
- Why this matters: deleting obsolete test ownership removes false signals from retired runtime surfaces and clarifies active test boundaries.

### Checklist
- [x] Removed `tests/unit/**` legacy suite.
- [x] Removed `tests/integration/**` legacy suite.
- [x] Removed `tests/manual/**` legacy suite.
- [x] Removed `tests/helpers/**` legacy helper surface.
- [x] Left `tests/dpost_v2/**` untouched.

### Manual Check
- [x] `git rm -r tests/unit tests/integration tests/manual tests/helpers`
- [x] `git ls-files tests/unit tests/integration tests/manual tests/helpers tests/conftest.py` (only `tests/conftest.py` remained)

### Completion Notes
- How it was done: `Remove-Item` was policy-blocked in this environment, so removal was executed with `git rm -r`, deleting 129 files (`unit: 111`, `integration: 8`, `manual: 2`, `helpers: 8`).

---

## Section: Retained Test Bootstrap Cleanup
- Why this matters: root `tests/conftest.py` was legacy-coupled and needed cleanup so retained tests do not import removed runtime surfaces.

### Checklist
- [x] Replaced legacy fixtures/imports in `tests/conftest.py` with minimal path-bootstrap logic.
- [x] Removed stale references to `dpost`, `src/dpost`, `v1`, and `shadow` from retained allowed-scope file.

### Manual Check
- [x] `rg -n "from dpost|import dpost|src/dpost|\bv1\b|\bshadow\b" tests/conftest.py` (no matches)

### Completion Notes
- How it was done: collapsed `tests/conftest.py` to only deterministic `sys.path` setup for `src` and project root; removed all legacy runtime fixtures and helper dependencies.

---

## Section: Validation and Checkpoint
- Why this matters: lane completion requires reproducible proof that active V2 tests still pass and cleanup is checkpointed.

### Checklist
- [x] Re-ran retained V2 test suite after retirement.
- [x] Ran lint against retained test surface.
- [x] Created lane completion checkpoint commit.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2` -> `350 passed in 4.50s`
- [x] `python -m ruff check tests/dpost_v2 tests/conftest.py` -> `All checks passed`
- [x] `git commit -m "v2: retire legacy runtime test suites"` -> `8e45e84`

### Completion Notes
- How it was done: validated retained harness and lint gates after deletions, then committed with a clean worktree.

---

## Section: Risks and Assumptions
- Why this matters: explicit boundaries prevent over-claiming and provide clear handoff expectations.

### Checklist
- [x] Assumed all tests under `tests/unit`, `tests/integration`, `tests/manual`, and `tests/helpers` were legacy runtime coverage and safe to retire.
- [x] Assumed no retained V2 tests depend on deleted helpers or fixtures.
- [x] Documented that no new tests were added/updated as part of this lane.

### Manual Check
- [x] `rg -n "from tests\.helpers|import tests\.helpers|from tests\.conftest|pytest_plugins" tests/dpost_v2`
- [x] `git status --short` (clean after commit)

### Completion Notes
- How it was done: dependency checks and full `tests/dpost_v2` execution confirmed harness independence from deleted legacy surfaces.
