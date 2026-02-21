# Final Manual Validation Runbook

## Purpose
- Provide one operator-facing checklist to close both:
  - full legacy repo retirement validation
  - Part 3 domain extraction validation

## Preconditions
- Work from repository root with environment configured.
- Automated gates already green:
  - `python -m pytest -m migration`
  - `python -m pytest`
  - `python -m ruff check .`
  - `python -m black --check .`

## Execution Status
- Operator-reported manual validation completion date: 2026-02-21.

## Manual Checks

### 1. Desktop Runtime Smoke
- Why this matters: validates Tk/UI interactions after deep ownership moves.
- Steps:
  1. Set required env vars (`PC_NAME`, `DEVICE_PLUGINS`, optional `DPOST_RUNTIME_MODE=desktop`).
  2. Run `python -m dpost`.
  3. Drop one valid and one invalid file into watch path.
  4. Confirm:
     - valid file routes to destination record path
     - invalid file follows rename/exception workflow with expected dialogs
     - app closes cleanly.

### 2. Headless Runtime Smoke
- Why this matters: confirms default production posture remains stable.
- Steps:
  1. Set `DPOST_RUNTIME_MODE=headless` (and required plugin vars).
  2. Run `python -m dpost`.
  3. Process representative valid/invalid files.
  4. Confirm:
     - processing occurs without UI dependencies
     - logs/metrics endpoints respond as expected
     - shutdown path is clean.

### 3. Plugin Family Spot Checks
- Why this matters: validates extracted domain batch/routing behavior across real processors.
- Steps:
  1. Run at least three representative plugin families (include one staged/batch flow such as PSA or Kinexus).
  2. Confirm routing, record naming, and output artifacts match expected device behavior.
  3. Trigger one unknown-plugin configuration and confirm actionable failure messaging.

### 4. Records/Sync Failure Scenario
- Why this matters: ensures persistence + retry/error behavior was preserved.
- Steps:
  1. Force sync backend failure condition (e.g., invalid credentials/endpoint).
  2. Process files that create/append records.
  3. Confirm:
     - records persist locally
     - files remain tracked as unsynced where expected
     - user-facing error path is actionable
     - retry behavior remains intact after failure clears.

### 5. Contributor Cold-Read
- Why this matters: confirms docs are sufficient without legacy tracing.
- Steps:
  1. Read `README.md`, `DEVELOPER_README.md`, and architecture docs in order.
  2. Confirm a new contributor can:
     - start runtime
     - understand plugin boundaries
     - locate migration/retirement status
     - avoid using any `ipat_watchdog` path.

## Evidence Template
- Date:
- Operator:
- Environment:
- Desktop runtime smoke: Pass/Fail + notes
- Headless runtime smoke: Pass/Fail + notes
- Plugin spot checks: Pass/Fail + notes
- Records/sync failure scenario: Pass/Fail + notes
- Contributor cold-read: Pass/Fail + notes
- Follow-up actions:
