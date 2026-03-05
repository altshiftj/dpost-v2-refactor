# Checklist: V2 Manual Launch Validation

## Objective
- Validate the `dpost` command as the canonical V2 launcher after CLI rename migration.
- Confirm startup remains stable for `v2` mode and retired-mode rejection still works.
- Establish a repeatable manual baseline before continuing runtime/device hardening.

## Reference Set
- [docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md]
- [docs/checklists/20260304-v2-startup-bootstrap-lane-checklist.md]
- [src/dpost/__main__.py](/d:/Repos/d-post/src/dpost/__main__.py)
- [src/dpost_v2/__main__.py](/d:/Repos/d-post/src/dpost_v2/__main__.py)

## Section: Environment and Branch Setup
- Why this matters: prevents false negatives from stale code or wrong checkout.

### Checklist
- [ ] On the expected branch/rebuild branch.
- [ ] Installed/active virtual environment matches project Python version.
- [ ] Repo is clean before start.

### Manual Check
- [ ] `git status --short --branch`
- [ ] `git rev-parse --abbrev-ref HEAD`
- [ ] `python --version`
- [ ] `python -m pip --version`

## Section: Canonical Launcher Contract
- Why this matters: makes `dpost` the primary command path and removes hidden entrypoint drift.

### Checklist
- [ ] Canonical entrypoint resolves to `dpost.__main__:main` (not `dpost_v2.__main__:main`).
- [ ] `--help` output remains coherent and does not regress mode contract.
- [ ] `--mode v2` is accepted and defaults are applied.
- [ ] Retired modes fail before startup.

### Manual Check
- [ ] `python -m dpost --help`
- [ ] `python -m dpost --mode v2 --headless --dry-run`
- [ ] `python -m dpost --mode v2 --profile default --dry-run`
- [ ] `python -m dpost --mode v1`
- [ ] `python -m dpost --mode shadow`

### Expected Output
- [ ] `python -m dpost --help` prints CLI usage.
- [ ] `python -m dpost --mode v2 --headless --dry-run` prints `dpost startup succeeded`.
- [ ] `python -m dpost --mode v1` exits with code `2` and mode-support error text.
- [ ] `python -m dpost --mode shadow` exits with code `2`.

## Section: Internal V2 Path Continuity
- Why this matters: keeps direct module path useful for dev and tests while branding defaults to `dpost`.

### Checklist
- [ ] `python -m dpost_v2 --mode v2 --headless --dry-run` remains executable.
- [ ] `src/dpost` module remains lightweight shim and does not contain runtime implementation logic.

### Manual Check
- [ ] `python -m dpost_v2 --mode v2 --headless --dry-run`
- [ ] `rg --line-number "from dpost_v2.__main__ import main|_run_v2|canonical" src/dpost/__main__.py`

## Section: Direct Entrypoint Regression
- Why this matters: ensures command and module invocation converge on the same startup behavior.

### Checklist
- [ ] `python -m dpost --mode v2 --headless --dry-run` and `python -m dpost_v2 --mode v2 --headless --dry-run` have matching success semantics.
- [ ] Failure paths continue to map to non-zero exit codes.

### Manual Check
- [ ] `python -m dpost --mode v2 --headless --dry-run`
- [ ] `python -m dpost_v2 --mode v2 --headless --dry-run`
- [ ] compare exit status: both should return `0` in dry-run mode.
- [ ] `python -m dpost_v2 --mode v1`

## Section: Smoke to Next Stage (v2 Runtime Behavior)
- Why this matters: confirms we can move from launch verification into runtime hardening.

### Checklist
- [ ] A minimal real startup attempt succeeds in dry-run mode with default profile.
- [ ] Real config launch path behaves deterministically (`--config`, `--headless` when provided).
- [ ] Exit behavior is stable (`0` on success, `1` on failure, `2` on invalid args/mode).

### Manual Check
- [ ] `dpost --mode v2 --headless --dry-run`
- [ ] `dpost --mode v2 --headless`
- [ ] `dpost --mode v2 --config <path-to-existing-config> --dry-run` (if a config file is available)

### Completion Notes
- [ ] Record observed startup mode (`desktop`/`headless`) and any warnings in notes.
- [ ] Note first failing stage if startup fails (settings/context/composition/runtime) and proceed to that trace file.

## Section: Checklist Gate
- Why this matters: explicit gate before moving into stabilization lane.

### Checklist
- [ ] All checks above marked complete.
- [ ] No direct changes required to `src/dpost_v2` startup contracts beyond planned hardening scope.

