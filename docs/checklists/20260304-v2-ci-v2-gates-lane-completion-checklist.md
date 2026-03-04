# Checklist: V2 CI-V2-Gates Lane Completion

## Objective
- Verify CI gate updates for V2 coverage growth were implemented safely, remained lightweight on rewrite lanes, and preserved strict required checks on `main`.

## Reference Set
- `docs/ops/lane-prompts/ci-v2-gates.md`
- `docs/planning/20260303-v2-codex-github-parallelization-runbook-rpc.md`
- `docs/planning/20260304-v2-ci-gates-alignment-rpc.md`
- `.github/workflows/public-ci.yml`
- `.github/workflows/rewrite-ci.yml`
- `.github/branch-protection/main.required-checks.json`

## Section: Public CI Main-Branch Gate Realignment
- Why this matters: required checks on `main` must fail closed against the active V2 tree and must not silently skip real test coverage.

### Checklist
- [x] Kept existing `Public CI` job names stable for required-check context compatibility.
- [x] Updated `quality` to check `src/dpost_v2` and `tests/dpost_v2` (when present).
- [x] Updated `unit-tests` to run `python -m pytest -q tests/dpost_v2`.
- [x] Updated `integration-tests` to run explicit V2 integration/smoke targets under `tests/dpost_v2`.
- [x] Updated `bootstrap-smoke` to run bootstrap-focused tests from `tests/dpost_v2`.
- [x] Converted prior skip behavior to fail-closed errors when required V2 paths are missing.

### Manual Check
- [x] Parse `.github/workflows/public-ci.yml` as YAML and confirm job map loads.
- [x] Verify `main.required-checks.json` contexts still map to unchanged `Public CI` job names.

### Completion Notes
- How it was done: replaced stale `tests/unit|integration/dpost_v2` paths with active `tests/dpost_v2` targets while preserving required check job names (`workflow-lint`, `quality (py3.12/3.13)`, `unit-tests (py3.12/3.13)`, `integration-tests (py3.12)`, `bootstrap-smoke`, `artifact-hygiene`).

---

## Section: Rewrite CI Lightweight + Trunk Integration Gates
- Why this matters: lane branches need fast signal, while `rewrite/v2` trunk still needs a stronger integration subset gate.

### Checklist
- [x] Added `rewrite-v2-quality` (`ruff` + `black --check`) for V2 paths.
- [x] Added `rewrite-v2-tests` quick suite (`tests/dpost_v2` with smoke excluded).
- [x] Added `rewrite-v2-integration` subset gate for `rewrite/v2` push/manual-dispatch only.
- [x] Kept existing rewrite hygiene/workflow-lint jobs intact.
- [x] Avoided brittle conditional logic by using explicit branch/event checks.

### Manual Check
- [x] Parse `.github/workflows/rewrite-ci.yml` as YAML and confirm expected jobs are present.
- [x] Confirm rewrite job names:
  - `rewrite-workflow-lint`
  - `rewrite-artifact-hygiene`
  - `rewrite-v2-quality`
  - `rewrite-v2-tests`
  - `rewrite-v2-integration`

### Completion Notes
- How it was done: introduced lightweight Linux-hosted V2 checks for rewrite lanes and a trunk-only integration reinforcement gate without changing `main` protection contexts.

---

## Section: Planning and Reporting Traceability
- Why this matters: CI gate behavior needs clear operator documentation so branch policy and workflow behavior remain auditable across lanes.

### Checklist
- [x] Updated runbook CI verification steps in `20260303-v2-codex-github-parallelization-runbook-rpc.md`.
- [x] Added planning RPC for gate decisions and rationale.
- [x] Added implementation report summarizing behavior changes, validations, and assumptions.

### Manual Check
- [x] Confirm planning/report docs reference both workflow files and lane prompt.

### Completion Notes
- How it was done: added aligned planning/report artifacts that document `main` strictness and rewrite-lane lightweight gating strategy.

---

## Section: Validation Gate
- Why this matters: lane completion requires evidence that V2 runtime code/tests still pass after CI gate changes.

### Checklist
- [x] V2 test suite passed locally.
- [x] V2 lint passed locally.
- [x] Workflow YAML parse checks passed locally.
- [x] Lane changes were committed as a scoped checkpoint.

### Manual Check
- [x] `python -m pytest -q tests/dpost_v2` -> `313 passed`
- [x] `python -m ruff check src/dpost_v2 tests/dpost_v2` -> `All checks passed!`
- [x] YAML parse sanity for `.github/workflows/public-ci.yml` and `.github/workflows/rewrite-ci.yml`

### Completion Notes
- How it was done: final lane checkpoint committed as `b7bea41` with message `v2: ci align main and rewrite gates`; no local blockers remained.

