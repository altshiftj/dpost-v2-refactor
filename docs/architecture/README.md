# Architecture Documentation Guide

## Purpose
- Keep architecture decisions, component boundaries, and domain vocabulary explicit throughout the `ipat_watchdog` -> `dpost` migration.
- Ensure every major change is discussed, documented, and traceable.

## Canonical Artifacts
- Baseline architecture snapshot:
- `docs/architecture/architecture-baseline.md`
- Dependency and layering rules:
- `docs/architecture/architecture-contract.md`
- Object and module responsibilities:
- `docs/architecture/responsibility-catalog.md`
- Architecture decisions:
- `docs/architecture/adr/`
- Migration-level findings and plans:
- `docs/reports/`
- `docs/planning/`
- `docs/checklists/`
- Test contract split:
- `tests/migration/` for `dpost` migration/cutover tests
- `tests/unit/`, `tests/integration/`, `tests/manual/` for legacy `ipat_watchdog` contract tests
- Vocabulary and term definitions:
- `GLOSSARY.csv`

## Update Protocol
1. Before implementing a major architectural change:
- Capture findings in a report (`docs/reports/`).
- Capture intent and approach in a plan (`docs/planning/`).
- Capture execution steps in a checklist (`docs/checklists/`).

2. When architecture direction changes:
- Add an ADR in `docs/architecture/adr/`.
- Reference impacted modules and tradeoffs.

3. After implementation reaches green:
- Refresh `architecture-baseline.md` if structure changed.
- Refresh `responsibility-catalog.md` if ownership changed.
- Add/adjust terms in `GLOSSARY.csv` for new project-defined vocabulary.

## Definition of Done for Architecture-impacting Work
- Tests/lint pass for changed scope.
- Architecture decision captured (ADR) when relevant.
- Responsibility ownership is documented.
- Vocabulary changes are reflected in `GLOSSARY.csv`.

## Test Isolation Commands
- Full suite:
- `python -m pytest`
- Legacy-only:
- `python -m pytest -m legacy`
- Migration-only:
- `python -m pytest -m migration`
