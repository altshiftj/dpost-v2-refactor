You are working in D:\Repos\d-post.

Lane: contracts-interfaces
Branch: rewrite/v2-lane-contracts-interfaces

Current phase is locked to pseudocode/docs completion only.
Do not edit src/ or tests/.

Allowed edits:
- docs/pseudocode/**
- docs/checklists/**
- docs/planning/**
- docs/reports/**
- GLOSSARY.csv

Required references:
- docs/planning/20260303-v2-cleanroom-rewrite-blueprint-rpc.md
- docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md
- docs/checklists/20260304-v2-pseudocode-population-checklist.md

Task:
Populate and normalize contract/interface pseudocode docs with concrete behavior intent and strict V1 traceability.
Every edited pseudocode file must include:
- Intent
- Inputs
- Outputs
- Invariants
- Failure Modes
- Pseudocode
- Tests To Implement
- explicit origin/source mapping to V1 where applicable

Rules:
- Remove TBD and placeholder-only language.
- Preserve V2 layer boundaries.
- Update checklist completion notes.
- Add glossary terms in GLOSSARY.csv when introducing new internal terms.

Output:
- Files changed
- Checks run (`rg "TBD" docs/pseudocode`, `rg "origin|source|v1" docs/pseudocode -n`)
- Remaining risks/blockers