# 20260305 V2 Post-Cleanup Stabilization Wave RPC

## Objective
- Stabilize V2 runtime quality after structural cleanup.
- Improve reliability, observability signal quality, and performance confidence.
- Avoid additional structural deletions unless a blocker requires them.

## Scope
- In scope:
  - Runtime resilience hardening (`src/dpost_v2/runtime/**`, `src/dpost_v2/application/runtime/**`)
  - Ingestion reliability and backpressure/error-path behavior
  - Observability signal quality (logging/metrics/tracing consistency)
  - CI signal quality and flake reduction for active V2 suites
- Out of scope by default:
  - Additional legacy tree deletions
  - Broad API redesign
  - New migration/mapping restructuring

## Workstreams
1. Runtime resilience
- Startup failure-mode determinism
- Graceful shutdown and interruption behavior
- Configuration edge-case hardening

2. Ingestion robustness
- Retry/failure-path determinism
- Stage contract invariants and idempotency
- Integration smoke stability

3. Observability quality
- Error taxonomy normalization in logs/events
- Metric cardinality and naming consistency
- Trace/event correlation quality checks

4. CI reliability
- Keep rewrite/public gates aligned to active V2 surfaces
- Reduce flaky tests and timing-sensitive assertions
- Preserve stable required check names

## Delivery Rules
- TDD required for behavior changes.
- Lane-scoped commits and deterministic test updates.
- No structural deletions unless explicitly raised as blocker with rationale.

## Exit Criteria
- Active V2 checks remain green after hardening slices.
- No new unstable/flaky tests introduced.
- Observability/runtime failure diagnostics are clearer than baseline.
