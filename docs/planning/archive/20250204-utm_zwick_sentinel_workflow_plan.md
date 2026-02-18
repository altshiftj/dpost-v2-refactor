# Plan Template

## Goal
- Accept `.zs2` files with a `usr-inst-sample_name` prefix and trigger processing only when the sentinel `.xlsx` arrives, producing a record containing both artifacts.

## Non-Goals
- Change core record routing or directory layout.
- Add new UI workflows.

## Constraints
- Filename prefix must remain compatible with existing record routing (`user` + `institute` + `sample`).
- Processor should remain safe for concurrent filesystem events.

## Approach
- Validate or normalize `usr-inst-sample_name` during preprocessing.
- Stage `.zs2` by prefix and release on sentinel `.xlsx`.
- Update processing to move `.zs2` + `.xlsx` with unique naming and correct datatype.
- Remove `.csv`/`.txt` handling from Zwick processor.
- Update probes/configuration and tests accordingly.

## Milestones
- Add failing unit tests for sentinel workflow.
- Implement preprocessing + processing updates.
- Update config/probes and integration tests.

## Dependencies
- Sentinel `.xlsx` must match `.zs2` prefix exactly.
- Enforce a 30-minute TTL to flush `.zs2` when no sentinel appears.
- Primary `datatype` is `xlsx`.

## Risks and Mitigations
- Prefix mismatch -> log and ignore invalid artifacts with clear warnings.
- Sentinel never arrives -> enforce TTL-based flush and sync after 30 minutes.
- Breaking tests -> update unit/integration tests in the same change set.

## Test Plan
- Unit tests for staging/trigger and processing outputs.
- Integration tests covering end-to-end record creation.

## Rollout / Validation
- Run `python -m pytest` locally.
- Verify new records contain `.zs2` and `.xlsx` only.
