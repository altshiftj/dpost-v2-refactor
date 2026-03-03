# RPC: Legacy Seams Freshness Posture and De-Patchwork Strategy

## Date
- 2026-03-03

## Status
- Draft for Review

## Context
- The codebase has completed major migration and boundary hardening work into canonical `src/dpost/**` ownership.
- Architecture is now explicitly layered and governed by:
  - `docs/architecture/architecture-baseline.md`
  - `docs/architecture/architecture-contract.md`
  - `docs/architecture/responsibility-catalog.md`
- Remaining concern: parts of the implementation still feel like migration-era patchwork, especially around orchestration seams and compatibility affordances.

## Why This Matters
- OSS contributors need code that is easy to trust, trace, and change safely.
- "Patchwork smell" increases onboarding time and raises fear-of-change even when behavior is stable.
- We want the code to feel deliberate and cohesive ("fresh bread"), not incidental.

## Freshness Definition (Operational)
- A module is "fresh" when:
  - dependencies are explicit,
  - ownership is clear,
  - side effects are isolated behind contracts,
  - there is a single obvious place to change behavior,
  - tests map cleanly to that ownership boundary.

## Evidence Snapshot (Current Seams)
1. Ambient config lifecycle seam still exists
- `src/dpost/application/config/context.py` still exposes `init_config/get_service/current/reset_service`.
- Production startup now constructs `ConfigService` directly, but context helpers remain available and still appear in tests/manual flows.

2. Pipeline runtime proxies manager-private methods
- `src/dpost/application/processing/processing_pipeline_runtime.py` routes stage behavior through `FileProcessManager` private methods.
- Works, but retains migration-style coupling shape.

3. Startup settings ownership is split
- `src/dpost/runtime/bootstrap.py` and `src/dpost/runtime/startup_config.py` both participate in startup settings resolution logic.
- Boundary is improved but still not fully single-owner in feel.

4. Compatibility-friendly helper signatures remain in hot paths
- `src/dpost/infrastructure/storage/filesystem_utils.py` retains broad optional/contextual parameters for some helpers.
- Explicit context is now common, but signatures still reflect transitional flexibility.

## Assessment
- Severity: **moderate, controlled**, not crisis-level architecture debt.
- Behavior risk: low right now (suite is stable), but maintainability risk grows over time if seams remain unfocused.
- A full rewrite is not warranted.

## Decision
- Do a **targeted freshness pass**, not a structural rewrite.
- Preserve behavior; reduce ambiguity.
- Prioritize changes that improve contributor clarity per line changed.

## Strategy (Ordered Slices)
1. Config lifecycle containment
- Goal: confine ambient context helpers to explicitly non-production use.
- Direction:
  - keep production paths on direct `ConfigService` construction and injection,
  - mark `config.context` as compatibility/testing seam in docs and enforce no new production dependencies.

2. Pipeline collaborator hardening
- Goal: reduce private-method proxy feel between `_ProcessingPipeline` and `FileProcessManager`.
- Direction:
  - keep stage flow in `processing_pipeline.py`,
  - move side-effect operations behind explicit runtime-port methods that do not mirror manager-private names.

3. Startup settings ownership consolidation
- Goal: one obvious owner for startup settings parsing/validation.
- Direction:
  - retain `composition.py` as orchestrator,
  - consolidate parsing/validation policy into one helper boundary and keep `bootstrap.py` focused on runtime assembly.

4. Helper signature narrowing (storage/naming)
- Goal: remove transitional optionality where runtime context is always explicit.
- Direction:
  - tighten function signatures in high-traffic helper APIs to required explicit context only,
  - keep compatibility wrappers only where proven necessary by real call sites.

## Non-Goals
- No behavior changes in processing/routing/sync semantics.
- No broad file moves or cosmetic rewrites.
- No architecture-contract direction changes.

## Acceptance Criteria
- Existing behavior preserved (unit + integration + manual lane remain green).
- For each seam cleaned, there is one obvious owner/module for future edits.
- No new production reliance on ambient config context.
- Runtime pipeline contracts become clearer without increasing stage sprawl.
- Responsibility changes (if any) are reflected in `docs/architecture/responsibility-catalog.md`.

## Suggested Execution Order
1. Tighten and document config lifecycle containment.
2. Harden pipeline runtime contract naming/ownership.
3. Consolidate startup settings ownership.
4. Narrow helper signatures and delete residual low-value compatibility branches.

## Validation Commands
- `python -m ruff check .`
- `python -m black --check src tests`
- `python -m pytest -q tests/unit`
- `python -m pytest -q tests/integration`
- `python -m pytest -q -m manual tests/manual`

## References
- `docs/architecture/architecture-baseline.md`
- `docs/architecture/architecture-contract.md`
- `docs/architecture/responsibility-catalog.md`
- `docs/planning/20260303-processing-sprawl-posture-rpc.md`
- `docs/planning/20260224-naming-settings-single-source-of-truth-rpc.md`

## Slice Artifacts
1. Config lifecycle containment
- Report: `docs/reports/20260303-config-lifecycle-containment-slice-report.md`
- Checklist: `docs/checklists/20260303-config-lifecycle-containment-slice-checklist.md`

2. Pipeline collaborator hardening
- Report: `docs/reports/20260303-pipeline-collaborator-hardening-slice-report.md`
- Checklist: `docs/checklists/20260303-pipeline-collaborator-hardening-slice-checklist.md`

3. Startup settings ownership consolidation
- Report: `docs/reports/20260303-startup-settings-ownership-consolidation-slice-report.md`
- Checklist: `docs/checklists/20260303-startup-settings-ownership-consolidation-slice-checklist.md`

4. Helper signature narrowing (storage/naming)
- Report: `docs/reports/20260303-helper-signature-narrowing-storage-naming-slice-report.md`
- Checklist: `docs/checklists/20260303-helper-signature-narrowing-storage-naming-slice-checklist.md`
