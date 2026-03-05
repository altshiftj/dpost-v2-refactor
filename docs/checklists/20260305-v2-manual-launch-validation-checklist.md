# Checklist: V2 Manual Launch Validation

## Objective
- Validate the `dpost` command as the canonical V2 launcher after CLI rename migration.
- Confirm startup remains stable for `v2` mode and retired-mode rejection still works.
- Establish a repeatable manual baseline before continuing runtime/device hardening.

## Reference Set
- [docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md](/d:/Repos/d-post/docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md)
- [docs/checklists/20260304-v2-startup-bootstrap-lane-checklist.md](/d:/Repos/d-post/docs/checklists/20260304-v2-startup-bootstrap-lane-checklist.md)
- [src/dpost/__main__.py](/d:/Repos/d-post/src/dpost/__main__.py)
- [src/dpost_v2/__main__.py](/d:/Repos/d-post/src/dpost_v2/__main__.py)
- [configs/dpost-v2.config.json](/d:/Repos/d-post/configs/dpost-v2.config.json)

## Section: Environment and Branch Setup
- Why this matters: prevents false negatives from stale code or wrong checkout.

### Checklist
- [x] On `rewrite/v2-lane-legacy-cleanup-rebuild`.
- [x] Python 3.12.7 in active venv (`python --version`).
- [x] Repo clean before final validation checkpoint.

### Manual Check
- [x] `git status --short --branch`
- [x] `git rev-parse --abbrev-ref HEAD`
- [x] `python --version`
- [x] `python -m pip --version`

## Section: Canonical Launcher Contract
- Why this matters: makes `dpost` the primary command path and removes hidden entrypoint drift.

### Checklist
- [x] Canonical entrypoint resolves to `dpost.__main__:main` (not `dpost_v2.__main__:main`).
- [x] `--help` output remains coherent and does not regress mode contract.
- [x] `--mode v2` is accepted and defaults are applied.
- [x] Retired modes fail before startup.

### Manual Check
- [x] `python -m dpost --help`
- [x] `python -m dpost --mode v2 --headless --dry-run`
- [x] `python -m dpost --mode v2 --profile default --dry-run`
- [x] `python -m dpost --mode v1`
- [x] `python -m dpost --mode shadow`

### Expected Output
- [x] `python -m dpost --help` prints CLI usage.
- [x] `python -m dpost --mode v2 --headless --dry-run` prints `dpost startup succeeded`.
- [x] `python -m dpost --mode v1` fails with CLI invalid-choice error.
- [x] `python -m dpost --mode shadow` fails with CLI invalid-choice error.

## Section: Internal V2 Path Continuity
- Why this matters: keeps direct module path useful for dev and tests while branding defaults to `dpost`.

### Checklist
- [x] `python -m dpost_v2 --mode v2 --headless --dry-run` remains executable.
- [x] `src/dpost` module remains lightweight shim and does not contain runtime implementation logic.

### Manual Check
- [x] `python -m dpost_v2 --mode v2 --headless --dry-run`
- [x] `rg --line-number "from dpost_v2.__main__ import main|_run_v2|canonical" src/dpost/__main__.py`

## Section: Direct Entrypoint Regression
- Why this matters: ensures command and module invocation converge on the same startup behavior.

### Checklist
- [x] `python -m dpost --mode v2 --headless --dry-run` and `python -m dpost_v2 --mode v2 --headless --dry-run` have matching success semantics.
- [x] Failure paths continue to map to non-zero exit codes.

### Manual Check
- [x] `python -m dpost --mode v2 --headless --dry-run`
- [x] `python -m dpost_v2 --mode v2 --headless --dry-run`
- [x] Compare exit status: both return `0` in dry-run mode.
- [x] `python -m dpost_v2 --mode v1`

## Section: Smoke to Next Stage (v2 Runtime Behavior)
- Why this matters: confirms we can move from launch verification into runtime hardening.

### Checklist
- [x] A minimal real startup attempt succeeds in dry-run mode with default profile.
- [x] Real config launch path behaves deterministically (`--config`, `--headless` when provided).
- [x] Exit behavior is stable (`0` on success, `1` on failure, `2` on invalid args/mode).

### Manual Check
- [x] `dpost --mode v2 --headless --dry-run`
- [x] `dpost --mode v2 --headless`
- [x] `dpost --mode v2 --config .\configs\dpost-v2.config.json --dry-run`
- [x] `dpost --mode v2 --config .\configs\dpost-v2.config.json --headless`

### Completion Notes
- [x] Observed startup mode was `headless` in CLI dry-run and non-dry-run checks.
- [x] No startup warnings were observed during successful baseline runs.
- [x] First-failing-stage check was not reached in successful baseline.

## Section: Checklist Gate
- Why this matters: explicit gate before moving into stabilization lane.

### Checklist
- [x] All checks above marked complete.
- [x] No direct changes required to `src/dpost_v2` startup contracts beyond planned hardening scope in this wave.

## Section: Patching Log (Executed)
- [x] Added patchable `run` wrapper/symbol compatibility in `src/dpost_v2/__main__.py` (module exports and delegation path).
- [x] Kept `run` usage centralized in `main()` so legacy monkeypatch expectations and `src/dpost` delegation remain deterministic.
- [x] Updated `tests/dpost_v2/test___main__.py` to clear stale launch env (`DPOST_MODE`, `DPOST_PROFILE`, `DPOST_CONFIG`) in legacy delegation test.
- [x] Committed stabilization checkpoint and launch config example:
  - `5b9de7c` – `v2: stabilize manual launch and entrypoint testability`
  - `eeca785` – `chore: add v2 launch config example`

### Notes for Cleanup
- This checklist is now the canonical historical artifact for the launch-validation wave.
- Before cleanup merge, verify:
  - [ ] All pre/post cleanup branches include this file.
  - [ ] Legacy `src/dpost` behavior remains shim-only.
  - [ ] Required checks re-run once post-merge: `python -m pytest -q tests/dpost_v2`.