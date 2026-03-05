# 20260305 V2 PC/Device Runtime Wiring RPC

## Goal
- Wire V2 runtime so `dpost --mode v2 --profile prod --headless` can execute real ingestion behavior with PC-plugin-owned device scope and process at least one file deterministically.

## Non-Goals
- Broad architecture redesign across all layers.
- Reintroduction of legacy runtime modes (`v1`, `shadow`).
- Bulk refactor outside runtime/startup/ingestion/plugin integration seams.

## Constraints
- Keep work in V2 surfaces (`src/dpost_v2/**`, `tests/dpost_v2/**`).
- Preserve existing startup success/failure contract and deterministic exit behavior.
- Maintain TDD for all behavior changes.
- Keep plugin contracts and stage boundaries stable.

## Approach
- Slice 1: Lock runtime execution contract with failing tests.
- Slice 2: Replace default noop ingestion binding in runtime composition with real ingestion engine wiring.
- Slice 3: Introduce deterministic headless event-source behavior for manual validation.
- Slice 4: Integrate PC-plugin workstation policy for device selection, and keep sync transport in backend adapters.
- Slice 5: Validate manual runbook and finalize stabilization checklist/report updates.

## Milestones
- M1: Startup bootstrap returns runnable runtime handle and non-dry-run path executes runtime loop under tests.
- M2: Composition builds real ingestion engine/stage handlers and passes runtime/ingestion suites.
- M3: Deterministic headless event source processes sample event/file path and emits stable outcomes.
- M4: Manual validation passes for one concrete workstation/device scope (`horiba_blb` owning `psa_horiba`) and evidence is documented.

## Dependencies
- Existing ingestion stage modules under `src/dpost_v2/application/ingestion/**`.
- Existing plugin host/discovery contracts under `src/dpost_v2/plugins/**`.
- Existing startup settings/context contracts under `src/dpost_v2/application/startup/**`.
- Existing runtime composition contract under `src/dpost_v2/runtime/composition.py`.

## Risks and Mitigations
- Risk: Runtime wiring destabilizes current startup pass path.
  - Mitigation: Keep dry-run behavior unchanged and add dedicated tests for dry-run vs non-dry-run.
- Risk: Stage/processor contracts mismatch at runtime composition boundaries.
  - Mitigation: Add integration tests that exercise real stage transitions with plugin-selected processors.
- Risk: PC plugin and sync backend responsibilities get conflated.
  - Mitigation: enforce PC plugin as policy/payload-shaping only; keep outbound transport ownership in sync backend.
- Risk: Headless loop semantics become nondeterministic.
  - Mitigation: Start with deterministic single-pass event-source mode for manual checks.

## Test Plan
- Focused:
  - `python -m pytest -q tests/dpost_v2/test___main__.py tests/dpost_v2/runtime tests/dpost_v2/application/runtime tests/dpost_v2/application/ingestion`
- Plugin integration:
  - `python -m pytest -q tests/dpost_v2/plugins/test_discovery.py tests/dpost_v2/plugins/test_device_integration.py tests/dpost_v2/plugins/test_host.py`
- Quality gates:
  - `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - `python -m pytest -q tests/dpost_v2`

## Pseudocode Linkage
- Canonical design spec root: `docs/pseudocode/`
- Runtime composition and dependencies:
  - `docs/pseudocode/runtime/composition.md`
  - `docs/pseudocode/runtime/startup_dependencies.md`
- Entrypoint behavior:
  - `docs/pseudocode/__main__.md`
- Application orchestration:
  - `docs/pseudocode/application/runtime/`
  - `docs/pseudocode/application/ingestion/`
  - `docs/pseudocode/application/startup/`
- Plugins:
  - `docs/pseudocode/plugins/discovery.md`
  - `docs/pseudocode/plugins/host.md`
  - `docs/pseudocode/plugins/profile_selection.md`

## Rollout / Validation
- Phase 1: land test-first runtime execution contract.
- Phase 2: land real ingestion engine composition wiring.
- Phase 3: validate manual PC/device pair processing path.
- Phase 4: run full V2 test/lint gates and update readiness report/checklist with final evidence.
