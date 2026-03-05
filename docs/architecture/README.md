# Architecture Documentation Guide

## Purpose

- Keep V2 architecture boundaries explicit for the canonical `dpost` runtime.
- Keep ownership, layering, and extension contracts stable as implementation
  evolves.

## Canonical Artifacts

- Baseline snapshot: `docs/architecture/architecture-baseline.md`
- Layer contract: `docs/architecture/architecture-contract.md`
- Extension contracts: `docs/architecture/extension-contracts.md`
- Responsibility ownership: `docs/architecture/responsibility-catalog.md`
- Narrative walkthrough: `docs/architecture/20260303-architecture-overview-and-code-story.md`
- Architecture decisions: `docs/architecture/adr/`
- Risk/status reports: `docs/reports/`
- Execution checklists: `docs/checklists/`
- Vocabulary: `GLOSSARY.csv`

## Active Code/Test Scope

- Runtime/package source of truth: `src/dpost_v2/`
- Active verification suites: `tests/dpost_v2/`

Archived lanes may still exist in the repository for historical traceability but
are not the active architecture target.

## Update Protocol

1. Before major architecture changes:
- capture findings in `docs/reports/`
- capture approach in `docs/planning/`
- capture execution steps in `docs/checklists/`

2. When direction changes:
- add/update ADR entries
- document rationale and tradeoffs

3. After implementation is green:
- refresh baseline and responsibility docs when ownership changed
- update glossary for new internal terms

## Definition of Done (Architecture-impacting Work)

- Changed-scope checks pass (`ruff`/`pytest` for active V2 targets).
- Ownership updates are documented.
- ADR updated when policy/direction changed.
- Glossary updated when new terms are introduced.

## Suggested Validation Commands

```powershell
python -m ruff check src/dpost_v2 tests/dpost_v2
python -m pytest -q tests/dpost_v2
```
