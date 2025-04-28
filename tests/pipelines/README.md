# Local Pipeline Simulation Scripts

This folder contains PowerShell scripts that simulate the full GitLab CI/CD pipeline locally.

## Available Scripts

- **simulate_build.ps1** — Builds the app locally using PyInstaller.
- **simulate_deploy.ps1** — Deploys the built executable to a target machine (or localhost).
- **simulate_run.ps1** — Remotely registers and starts the scheduled task on the target.
- **simulate_health.ps1** — Checks if the Watchdog service becomes healthy.
- **simulate_full_pipeline.ps1** — Runs all stages (build ➔ deploy ➔ run ➔ health) in sequence.

## Running the Full Pipeline

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\simulate_full_pipeline.ps1
```

If any stage fails, the simulation will stop immediately.

## Requirements

- PowerShell
- Python 3.12
- PuTTY tools (pscp.exe, plink.exe)
- Target machine with SSH enabled (can be localhost)

---

Good luck and happy shipping! 🎉
