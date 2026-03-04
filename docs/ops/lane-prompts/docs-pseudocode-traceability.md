You are working in D:\Repos\d-post.

Lane: docs-pseudocode-traceability
Branch: rewrite/v2-lane-docs-pseudocode-traceability

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
Drive pseudocode completeness and traceability across all V2 pseudocode docs, ensuring each file has concrete behavior and V1 mapping.
Every edited pseudocode file must include the mandatory sections and explicit V1 origin/source mapping where applicable.

Rules:
- Remove TBD and placeholder-only language.
- Preserve V2 layer boundaries.
- Update checklist completion notes.
- Add glossary terms in GLOSSARY.csv when introducing new internal terms.

Output:
- Files changed
- Checks run (`rg "TBD" docs/pseudocode`, `rg "origin|source|v1" docs/pseudocode -n`)
- Remaining risks/blockers