# Checklist: V2 Legacy Runtime Cutover Lane Completion

## Section: Retire Legacy Runtime Modes (`v1`, `shadow`)
- Why this matters: keeping retired runtime mode paths in the entrypoint risks accidental fallback to non-canonical startup behavior.

### Checklist
- [x] Update entrypoint tests to treat `v1` and `shadow` as retired modes.
- [x] Add deterministic assertions that bootstrap does not run when retired modes are requested.
- [x] Cover both CLI (`--mode`) and environment (`DPOST_MODE`) retired-mode paths.

### Manual Check
- [x] Run `python -m pytest -q tests/dpost_v2/test___main__.py` and confirm retired-mode tests pass.
- [x] Verify tests assert `exit_code == 2` for retired-mode requests.

### Completion Notes
- How it was done: added parametrized tests in `tests/dpost_v2/test___main__.py` for `--mode v1|shadow` and `DPOST_MODE=v1|shadow`, with explicit assertions that startup bootstrap is not called and failures are stable.

---

## Section: Enforce V2-Only Entrypoint Behavior
- Why this matters: the cutover requires a single runtime mode surface so operational behavior is deterministic and migration drift is prevented.

### Checklist
- [x] Restrict supported runtime modes in `src/dpost_v2/__main__.py` to `v2` only.
- [x] Keep unsupported environment mode errors explicit (`Unsupported runtime mode: <token>`).
- [x] Preserve existing exit-code semantics for parser errors, startup failures, and interrupts.

### Manual Check
- [x] Verify `src/dpost_v2/__main__.py` defines `_SUPPORTED_MODES = frozenset({"v2"})`.
- [x] Confirm tests still pass for failure/interrupt mappings (`exit_code == 1`) and parser/env rejection (`exit_code == 2`).

### Completion Notes
- How it was done: changed mode support to V2-only while leaving main() exception/result mapping unchanged, so success remains `0`, startup failures remain `1`, and invalid/unsupported modes remain `2`.

---

## Section: Preserve `dpost` CLI Compatibility
- Why this matters: runtime internals moved to V2, but operator-facing command expectations must remain `dpost`.

### Checklist
- [x] Set argparse program name to `dpost`.
- [x] Update startup success/failure output text to `dpost` wording.
- [x] Add test coverage asserting the success line uses `dpost` and not `dpost_v2`.

### Manual Check
- [x] Confirm parser usage text includes `usage: dpost` when mode validation fails.
- [x] Confirm `test_main_success_message_uses_dpost_command_name` passes.

### Completion Notes
- How it was done: updated parser `prog` and user-facing startup lines in `src/dpost_v2/__main__.py`, and added assertions in `tests/dpost_v2/test___main__.py` for command-name compatibility.

---

## Section: Lane Validation and Checkpoint
- Why this matters: lane completion requires deterministic quality gates and a reviewable checkpoint.

### Checklist
- [x] Run focused entrypoint test suite.
- [x] Run startup suite to detect startup contract regressions.
- [x] Run lane lint/test commands across `src/dpost_v2` and `tests/dpost_v2`.
- [x] Commit lane slice with scoped message.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/test___main__.py` -> `10 passed`.
- [x] `python -m pytest -q tests/dpost_v2/application/startup` -> `23 passed`.
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2` -> `All checks passed`.
- [x] `python -m pytest -q tests/dpost_v2` -> `355 passed`.
- [x] `git show --stat --oneline 9d68eaa` shows only `src/dpost_v2/__main__.py` and `tests/dpost_v2/test___main__.py` changed for the runtime cutover commit.

### Completion Notes
- How it was done: executed full validation gates after TDD red->green cycle and checkpointed with commit `9d68eaa` (`v2: startup retire legacy runtime entry modes`).
