# Checklist: Startup Settings Ownership Consolidation Slice

## Objective
- Consolidate startup settings parse/validation logic under one clear owner while preserving current startup behavior.

## Section 1: Ownership Delineation
- Why this matters: contributors should know exactly where startup setting rules live.

### Checklist
- [ ] Choose and document single owner module for startup setting policy.
- [ ] Remove duplicate parse/validation logic from non-owner module.
- [ ] Keep `StartupSettings` as the shared contract boundary used by composition/bootstrap.

### Completion Notes
- How it was done: _pending_

---

## Section 2: Precedence and Fallback Stability
- Why this matters: startup behavior is user-visible and high-sensitivity for operators.

### Checklist
- [ ] Add/adjust tests for explicit args vs `DPOST_*` env precedence.
- [ ] Verify fallback to base startup settings remains unchanged when no overrides are provided.
- [ ] Confirm port coercion behavior remains consistent for invalid/empty values.

### Completion Notes
- How it was done: _pending_

---

## Manual Check
- Run:
  - `python -m pytest -q tests/unit/runtime/test_startup_config.py`
  - `python -m pytest -q tests/unit/runtime/test_bootstrap.py tests/unit/runtime/test_bootstrap_additional.py`
  - `python -m pytest -q tests/unit/runtime/test_composition.py`
