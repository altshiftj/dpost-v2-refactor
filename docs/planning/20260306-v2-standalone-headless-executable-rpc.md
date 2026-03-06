# Plan: V2 Standalone Headless Executable Slice

## Intent
- Shift the next functional slice from plugin parity to executable runtime posture.
- Target a V2-only standalone executable that can run headless on workstation PCs,
  stay resident, keep watching for files, and be packaged with PyInstaller.

## Current Baseline
- `python -m dpost --mode v2 --profile prod --headless` works end-to-end.
- The three target device flows are functionally green for the accepted parity
  scope:
  - `tischrem_blb -> sem_phenomxl2`
  - `zwick_blb -> utm_zwick`
  - `horiba_blb -> psa_horiba`
- `tests/dpost_v2` is green on `main`.
- Packaging support exists only as a legacy-oriented surface today:
  - `pyproject.toml` exposes the `build` extra with `pyinstaller`
  - `build/specs/*.spec` still target `src/ipat_watchdog/__main__.py`
- Headless runtime is still effectively a deterministic one-pass scan, not a
  resident watch loop suitable for background execution on PCs.

## Why This Slice Is Next
- A PyInstaller executable is not operationally useful if it starts, scans once,
  and exits.
- The next blocker is runtime posture, not more plugin behavior.
- Frozen packaging should be wired only after the resident headless contract is
  explicit, tested, and hosted behind a clean lifecycle boundary.

## Target Outcome
- A V2-built executable launched on a workstation can:
  - start headless without UI prompts
  - remain resident in a continuous watch loop
  - discover files arriving after startup
  - process supported files through the current V2 runtime path
  - shut down cleanly with deterministic exit behavior
  - run from a PyInstaller-built artifact without relying on legacy entrypoints

## Proposed Slice Boundary
1. Resident headless loop contract
- Introduce explicit one-shot vs continuous headless behavior.
- Do not overload ingestion retry settings for runtime loop policy.
- Default should remain deterministic and explicit.

2. Idle poll and shutdown contract
- Start with a polling loop, not an OS-specific file observer.
- Polling is simpler to freeze, easier to test, and keeps deterministic behavior.
- Add explicit stop semantics and clean shutdown for background usage.

3. Runtime host refactor
- Promote runtime lifecycle ownership into a first-class `RuntimeHost`.
- Keep `DPostApp` focused on application/runtime-loop orchestration only.
- Avoid compatibility bridges or shims that would need later cleanup.
- Make the CLI/bootstrap path talk to the host contract directly.

4. Frozen bootstrap/config contract
- Make config and path resolution work the same in source and frozen execution.
- Package the canonical entrypoint:
  - `src/dpost/__main__.py`
- Do not keep legacy `ipat_watchdog` PyInstaller specs as the authoritative path.

5. PyInstaller build baseline
- Add a V2-specific spec or build script.
- Build a first frozen artifact from the canonical `dpost` entrypoint.
- Prove a smoke path:
  - executable starts
  - executable runs headless
  - executable processes a probe file in a temp workspace

## TDD Order
1. Add failing runtime tests for continuous watch behavior.
2. Add failing tests for stop/shutdown lifecycle.
3. Add failing tests for the `RuntimeHost` contract and composition/bootstrap
   ownership.
4. Add failing startup/path tests for frozen-safe config resolution.
5. Add failing packaging smoke harness/tests where practical.
6. Implement minimal runtime/build changes to satisfy each layer in order.

## Definition Of Done
- `python -m dpost` supports both:
  - deterministic one-shot mode
  - continuous headless watch mode
- Runtime lifecycle ownership is explicit in a first-class `RuntimeHost`, not
  implicit in the app object.
- Continuous mode processes files that arrive after startup.
- A V2 PyInstaller artifact can run the headless watch path from a temp probe.
- The frozen build uses the canonical `dpost` entrypoint, not legacy
  `ipat_watchdog`.
- Runtime/test/docs/build artifacts are updated together.

## Explicit Non-Goals For This Slice
- Windows service installation
- Task Scheduler registration
- tray icon or operator UI
- auto-update
- desktop runtime changes
- deeper sync backend expansion beyond the current runtime contract

## Likely Design Direction
- Add explicit runtime loop settings such as:
  - run mode: `oneshot` vs `continuous`
  - poll interval seconds
  - optional idle timeout for tests/manual probes
- Keep headless event ordering deterministic per scan cycle.
- Preserve the current one-pass manual probe path for smoke tests.
- Treat the current app-owned shutdown hook as a validated behavior checkpoint,
  not the final architecture.

## Key Risks
- Frozen plugin discovery and hidden imports
- Logging/diagnostics visibility when running without a console window
- clean exit semantics under Ctrl+C and process termination
- avoiding accidental behavioral drift between source and frozen execution
- baking the current app-owned shutdown seam into packaging if the host refactor
  is skipped

## Recommended Execution Sections
1. Runtime loop contract
2. Shutdown/lifecycle contract
3. Runtime host refactor
4. Frozen bootstrap/config path contract
5. V2 PyInstaller build baseline
6. Manual workstation probe closeout

## Parallelization Posture
- Start single-lane.
- Do not parallelize sections 1, 2, and 3:
  - they share the same runtime/app/composition surfaces and will create
    semantic merge churn.
- After sections 1, 2, and 3 are green, partial parallelization becomes
  reasonable:
  - lane A: frozen bootstrap/config path contract
  - lane B: PyInstaller build baseline
- Manual workstation closeout should reunify into one lane again.
