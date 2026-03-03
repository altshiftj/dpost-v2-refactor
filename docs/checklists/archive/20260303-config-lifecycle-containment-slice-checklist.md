# Checklist: Config Lifecycle Containment Slice

## Objective
- Constrain ambient config lifecycle helpers to compatibility/testing usage and keep production runtime wiring explicit via `ConfigService` injection.

## Section 1: Boundary Clarification
- Why this matters: contributors need one obvious production path for config ownership and activation.

### Checklist
- [ ] Document `config.context` as compatibility/testing seam in architecture docs.
- [ ] Ensure `startup_dependencies` and composition/runtime modules do not import `config.context`.
- [ ] Add/extend guard tests to prevent new production imports of ambient context helpers.

### Completion Notes
- How it was done: _pending_

---

## Section 2: Test-Surface Alignment
- Why this matters: tests can still use lifecycle helpers, but the usage should be explicit and intentional.

### Checklist
- [ ] Keep integration/manual setup imports of `config.context` local and explicit.
- [ ] Confirm no accidental package-level re-export of lifecycle helpers in `dpost.application.config`.
- [ ] Verify config-context tests describe intended seam behavior.

### Completion Notes
- How it was done: _pending_

---

## Manual Check
- Run:
  - `rg -n "application\\.config\\.context" src/dpost/runtime src/dpost/infrastructure/runtime_adapters src/dpost/application/runtime -g "*.py"`
  - `python -m pytest -q tests/unit/application/config/test_context.py`
  - `python -m pytest -q tests/unit/infrastructure/runtime/test_startup_dependencies.py`
