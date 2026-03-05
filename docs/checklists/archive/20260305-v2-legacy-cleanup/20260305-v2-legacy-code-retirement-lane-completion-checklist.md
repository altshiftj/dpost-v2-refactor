# Checklist: V2 Legacy-Code-Retirement Lane Completion

## Objective
- Retire the legacy canonical implementation in `src/dpost/**` while keeping the `dpost` command operational on V2 and keeping repository import/build coherence for V2 execution.

## Reference Set
- `AGENTS.md` lane instructions for `legacy-code-retirement`
- `pyproject.toml` script mapping (`dpost = "dpost.__main__:main"`)
- Commits:
  - `39006ef` (`v2: bridge dpost CLI to v2 runtime`)
  - `2830417` (`v2: remove legacy dpost implementation tree`)
  - `445e0e5` (`v2: constrain dpost CLI to v2 mode`)

## Section: Preserve Command Contract While Retiring Legacy Runtime
- Why this matters: the command name stays `dpost`, so removing legacy modules must not break CLI invocation.

### Checklist
- [x] Replaced `src/dpost/__main__.py` with a V2 bridge that dispatches to `dpost_v2.__main__.main`.
- [x] Enforced retirement of legacy modes by rejecting `--mode v1` and `--mode shadow`.
- [x] Updated `dpost --help` behavior to advertise only `--mode {v2}`.
- [x] Kept `src/dpost/__init__.py` as a minimal placeholder package docstring.

### Manual Check
- [x] `PYTHONPATH=<worktree>/src python -m dpost --help`
- [x] `PYTHONPATH=<worktree>/src python -m dpost --mode v1`
- [x] `PYTHONPATH=<worktree>/src python -c "import dpost, dpost_v2; print('ok')"`

### Completion Notes
- How it was done: the entrypoint was converted from legacy bootstrap/composition to a strict forwarding shim to V2, with explicit retired-mode rejection and V2-only help output.

---

## Section: Remove Legacy Canonical Implementation Tree
- Why this matters: retirement requires deleting superseded V1/shadow implementation code to prevent drift and accidental re-entry.

### Checklist
- [x] Removed `src/dpost/application/**`.
- [x] Removed `src/dpost/domain/**`.
- [x] Removed `src/dpost/infrastructure/**`.
- [x] Removed `src/dpost/device_plugins/**`.
- [x] Removed `src/dpost/pc_plugins/**`.
- [x] Removed `src/dpost/plugins/**`.
- [x] Removed `src/dpost/runtime/**`.
- [x] Left only `src/dpost/__init__.py` and `src/dpost/__main__.py` in tracked sources.

### Manual Check
- [x] `git status --short`
- [x] `Get-ChildItem src/dpost -Recurse -File`

### Completion Notes
- How it was done: legacy directories were removed in a controlled git-tracked deletion commit after establishing the bridge entrypoint.

---

## Section: Lane-Scoped Validation
- Why this matters: retirement is only acceptable if V2 lane behavior remains green and reproducible.

### Checklist
- [x] Ran lane-scoped V2 tests with local worktree source path precedence.
- [x] Ran Ruff on retained `src/dpost` bridge files.
- [x] Verified clean git working tree after lane commits.

### Manual Check
- [x] `PYTHONPATH=<worktree>/src python -m pytest -q tests/dpost_v2 --confcutdir=tests/dpost_v2`
- [x] `PYTHONPATH=<worktree>/src python -m ruff check src/dpost src/__init__.py`
- [x] `git log --oneline -3`

### Completion Notes
- How it was done: checks were re-run with `PYTHONPATH` pinned to this worktree because global interpreter path order initially resolved another repository source path.

---

## Section: TDD and Scope Conformance
- Why this matters: lane quality gates require explicit accounting when no new tests are added and when edits are deletion-focused.

### Checklist
- [x] Added/updated tests only when required by behavior-lock needs.
- [x] No test files were added or modified because behavior was constrained to retirement and CLI bridging.
- [x] Avoided compatibility shims beyond the minimal `dpost` command bridge required by script mapping.
- [x] Kept implementation changes within allowed runtime retirement scope.

### Manual Check
- [x] `git show --name-status 39006ef`
- [x] `git show --name-status 2830417`
- [x] `git show --name-status 445e0e5`

### Completion Notes
- How it was done: retirement was delivered as three coherent commits separating bridge introduction, bulk deletion, and CLI help/mode tightening for reviewability.
