# Append Casing Canonicalization Plan (2026-02-18)

## Goal
- Keep append behavior stable when a later run uses different casing for the same logical sample name.
- Preserve record continuity and avoid case-driven path drift in destination naming.

## Why This Matters
- Record lookup is already case-insensitive, so case-only differences should not create operational surprises.
- Storage paths and file IDs currently inherit incoming prefix casing; this can split numbering lineage or cause case-collision behavior on Windows.

## Intended Behavior
- First successful record creation establishes canonical sample casing for that record.
- On append to an existing record, if incoming sample differs only by case, processing canonicalizes to the record's existing sample casing.
- If incoming sample differs beyond case, current rename/unappendable policy remains unchanged.
- Processor plugins remain focused on device-specific staging/transformation and do not own global naming policy.

## Proposed Integration Points
- Routing step resolves existing record as it does today.
- Before record-path/file-id derivation, core processing compares incoming sample and existing `record.sample_name` with case-insensitive equality.
- If case-only difference is detected, manager uses canonical prefix derived from the existing record for downstream path and ID generation.

## Non-Goals
- No processor-specific validation rules.
- No change to rename-dialog UX for non-case differences.
- No migration of existing stored paths.

## Acceptance Criteria
- Appending `usr-ipat-samplea` to an existing `usr-ipat-SampleA` record resolves to the same record and same path lineage (`.../UTM-SampleA`, `UTM-SampleA-XX.*`).
- Numbering remains monotonic for both raw and exported artefacts.
- Kadi title remains consistent with canonical sample casing.

## Risks
- Existing records with inconsistent historical casing may need a deterministic tie-break if multiple variants already exist.
- Any canonicalization rule must remain isolated to case-only differences to avoid changing current rename behavior.

## Validation Plan
- Add focused unit tests for case-only append canonicalization in core processing flow.
- Add integration test covering two-session append with case-only sample variation.
- Replay one manual device scenario with intentional case variation and verify destination naming continuity.
