# Checklist: V2 Tests-V2-Harness Lane Completion

## Objective
- Verify the V2 harness lane delivered deterministic fixtures, reusable test-support utilities, and parity-ready harness primitives in TDD order.

## Reference Set
- `docs/pseudocode/application/startup/context.md`
- `docs/pseudocode/runtime/startup_dependencies.md`
- `docs/pseudocode/runtime/composition.md`
- `docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md`
- `docs/ops/lane-prompts/tests-v2-harness.md`

## Section: Deterministic Fixture Foundation
- Why this matters: cross-lane tests need stable startup/runtime fixtures to avoid flaky behavior and duplicate local setup logic.

### Checklist
- [x] Added `tests/dpost_v2/conftest.py`.
- [x] Added deterministic fixtures for trace-id generation, fixed UTC time, and workspace-rooted settings.
- [x] Added factory fixtures for bootstrap request, startup settings/dependencies/context, and runtime context.
- [x] Added `pytest` import-mode hardening for duplicate-basename test modules in V2 tree.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/harness/test_fixtures.py`

### Completion Notes
- How it was done: wrote fixture behavior tests first, then implemented shared fixtures in `tests/dpost_v2/conftest.py` with fixed defaults (`trace-0001`, `2026-03-04T12:00:00+00:00`, process id `4242`).

---

## Section: Shared Harness Utilities
- Why this matters: reusable builders/doubles reduce copy-paste setup and keep harness behavior deterministic across startup/runtime/ingestion tests.

### Checklist
- [x] Added `tests/dpost_v2/_support/factories.py` for deterministic builders.
- [x] Added `tests/dpost_v2/_support/runtime_doubles.py` for recording factories and lifecycle adapters.
- [x] Added tests for utility behavior in `tests/dpost_v2/harness/test_factories.py` and `tests/dpost_v2/harness/test_runtime_doubles.py`.
- [x] Ensured default dependency builders emit composition-compatible adapter payloads (`kind` + backend tokens).

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/harness/test_factories.py tests/dpost_v2/harness/test_runtime_doubles.py`

### Completion Notes
- How it was done: implemented utilities after red-phase tests, then refined defaults to match current composition binding expectations while preserving deterministic call-order logging.

---

## Section: Golden Corpus and Parity Harness
- Why this matters: rewrite blueprint requires behavior-capture and differential parity tooling before full cutover confidence.

### Checklist
- [x] Added `tests/dpost_v2/_support/corpus.py` with schema validation and deterministic case loading.
- [x] Added sample golden fixture `tests/dpost_v2/harness/fixtures/golden_corpus.sample.json`.
- [x] Added `tests/dpost_v2/_support/parity.py` for case-level diffs, report metrics, and parity threshold assertions.
- [x] Added corpus/parity tests in `tests/dpost_v2/harness/test_corpus.py` and `tests/dpost_v2/harness/test_parity.py`.
- [x] Added corpus fixture path exposure via `v2_golden_corpus_path`.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/harness/test_corpus.py tests/dpost_v2/harness/test_parity.py`

### Completion Notes
- How it was done: started with failing tests for duplicate IDs, ordering, and mismatch deltas, then implemented minimal loader/diff utilities until parity reports and threshold failures behaved deterministically.

---

## Section: Smoke Harness Coverage
- Why this matters: smoke tests ensure harness abstractions work end-to-end with bootstrap/composition and parity runner entrypoints.

### Checklist
- [x] Added bootstrap smoke test `tests/dpost_v2/smoke/test_bootstrap_harness_smoke.py`.
- [x] Added parity smoke test `tests/dpost_v2/smoke/test_parity_harness_smoke.py`.
- [x] Kept smoke tests fixture-driven with no lane-external test edits.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/smoke`

### Completion Notes
- How it was done: smoke tests were added after harness primitives existed and were adjusted to run against current composition expectations without introducing behavior-test coupling.

---

## Section: Validation Gate
- Why this matters: lane handoff requires reproducible green checks on harness-owned paths and no regressions in the V2 test suite.

### Checklist
- [x] Harness and smoke suites pass.
- [x] Full `tests/dpost_v2` suite passes after harness integration.
- [x] Harness-scoped Ruff checks pass.
- [x] Residual non-harness lint issue captured explicitly.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2/harness tests/dpost_v2/smoke`
- [x] `python -m pytest -q tests/dpost_v2`
- [x] `python -m ruff check tests/dpost_v2/conftest.py tests/dpost_v2/_support tests/dpost_v2/harness tests/dpost_v2/smoke`
- [ ] `python -m ruff check src/dpost_v2 tests/dpost_v2` (currently fails outside harness scope in `tests/dpost_v2/runtime/test_composition.py` with `F821`)

### Completion Notes
- How it was done: final harness gate is green (`19 passed`), full V2 test suite is green (`216 passed`), and harness-scoped lint is clean; one pre-existing out-of-scope Ruff failure remains documented.

