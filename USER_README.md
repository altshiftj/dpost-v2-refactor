# IPAT Data Watchdog - User Guide

## What the Watchdog Does
IPAT Data Watchdog keeps an eye on your workstation's upload folder, checks that incoming files follow the required naming convention, files accepted artefacts into organised record directories, and synchronises the finished records with the Kadi database. It surfaces issues through quick pop-up dialogs, moves problematic files to clearly labelled folders, and exposes optional web endpoints for logs and metrics.

## Before You Start
- **Supported platform**: Windows 10 or later.
- **Network access**: the PC must be able to reach the Kadi server used by your organisation.
- **Permissions**: the user running the app must be allowed to create folders under `C:\Watchdog\` and on the Windows Desktop.
- **Configuration**: your IT/automation team will provide the correct `PC_NAME` (and, if needed, `DEVICE_PLUGINS`) for your workstation.
- **Distribution**: you can run the packaged executable provided for your PC, or start the Python module directly if you work from the source tree.

### Launching the Watchdog

| Option | Steps |
|--------|-------|
| Packaged build | Double-click the supplied `wd_<pc_name>.exe`. Ensure the `PC_NAME` environment variable is set beforehand if the package does not embed it. |
| Python environment | Activate the environment where `ipat_watchdog` is installed, set the variables below, then run `python -m ipat_watchdog` or the console script `ipat-watchdog`. |

Required environment variables:
```powershell
$env:PC_NAME = "tischrem_blb"    # Example value - use the name provided for your PC
# Optional: override the device list if you are testing
# $env:DEVICE_PLUGINS = "sem_phenomxl2"
```

When the application starts it will:
1. Create the required folder structure if it does not already exist.
2. Start a background file watcher on the configured upload directory (non-recursive).
3. Open a hidden Tkinter window (no taskbar icon); dialogs appear only when your attention is needed.
4. Start a metrics server on `http://localhost:8000/metrics`. If Flask/Waitress are installed, an observability UI will be available at `http://localhost:8001/logs` and `http://localhost:8001/health`.

## Daily Workflow
1. **Prepare your instrument** so it saves data into `Desktop\Upload\`. The watcher looks only at the top level of this folder.
2. **Name files correctly before they are written**. Each item must follow the pattern `user-institute-sample`.
3. **Let the Watchdog run** while you perform measurements. The app moves each accepted artefact into the organised record structure and uploads it to Kadi immediately after processing.
4. **Respond to prompts**. If a name is invalid, a rename dialog appears. Cancelling the dialog sends the file to `00_To_Rename` for manual correction.
5. **Close the app when finished**. Use the window close controls (or exit the packaged executable). The watcher will stop and metrics will record a clean shutdown.

## Required File Naming Pattern

Format: `user-institute-sample`

| Segment    | Requirement                            | Example      |
|------------|----------------------------------------|--------------|
| `user`     | Letters only (3+ recommended)          | `jfw`        |
| `institute`| Letters only                           | `ipat`       |
| `sample`   | Letters, digits, spaces, or underscores; max 30 characters | `polymer_batch_01` |

Examples:
- `jfw-ipat-polymer_batch_01.tiff`
- `abc-kit-layer_test_2025.csv`

Spaces in the sample segment are automatically converted to underscores for consistency. If the watcher cannot fix the name automatically it will prompt you to fill in the three fields or move the file aside for manual repair.

## Folder Layout
When running with the default settings the following structure is created:

```
C:\Watchdog\
|-- logs\watchdog.log                    # JSON log output
`-- record_persistence.json              # Internal bookkeeping

Desktop\
|-- Upload\                              # Drop new files here
`-- Data\
    |-- 00_To_Rename\                    # Files needing manual naming fixes
    |-- 01_Exceptions\                   # Files that failed processing
    `-- <INSTITUTE>\<USER>\<DEVICE?-SAMPLE>\   # Record folders
```

Record folders are upper-cased by institute and user, and the device abbreviation (if known) is prefixed to the sample part. Example: `Data\IPAT\JFW\SEM-polymer_batch_01`. Each folder contains the files moved by the device-specific processor plus any generated artefacts (e.g., ZIP archives for ELID exports). The app remembers processed records in `record_persistence.json` so that a restart continues where it left off.

## Understanding Status and Logs
- **On-screen dialogs**: rename requests, errors, and informational pop-ups appear as Tkinter dialogs.
- **Log file**: `C:\Watchdog\logs\watchdog.log` contains JSON entries for every action. Share this file with support if issues persist.
- **Observability web UI (optional)**: `http://localhost:8001/logs` offers a simple filterable log viewer; `http://localhost:8001/health` returns a small status JSON.
- **Metrics endpoint**: `http://localhost:8000/metrics` exposes counters and histograms (e.g., files processed, failures, session duration) for Prometheus/Grafana dashboards.

## How Kadi Synchronisation Works
After a record is populated, the Watchdog uses the configured credentials to connect to Kadi and upload new artefacts. When uploads fail the app logs the exception, shows an error dialog, and keeps the files locally; it will try again when further files arrive or when you restart the application.

## Troubleshooting
- **Nothing happens when files are saved**: confirm the app is running and that files are written directly into `Desktop\Upload` (no subfolders). Check the log for errors.
- **Files keep appearing in `00_To_Rename`**: the names do not match the required pattern. Use the rename dialog or rename the files manually and move them back into `Upload`.
- **Files end up in `01_Exceptions`**: processing or device-specific validation failed. Review the log entry for details and contact support if unsure.
- **Observability page not available**: Flask/Waitress are optional dependencies. If you need the web UI, ask IT to install the observability extras.
- **Kadi upload errors**: verify network connectivity and service credentials. The records remain in `Desktop\Data` until the next successful sync.
- **Accidentally closed the app**: restart it using the same steps as above; existing records will be detected and synced as needed.

## Getting Help
If you need assistance, prepare the following before contacting support:
- A short description of the issue.
- A copy of the relevant entries from `C:\Watchdog\logs\watchdog.log`.
- Any files sitting in `00_To_Rename` or `01_Exceptions`.
- Confirmation of the `PC_NAME` value you are using.

With this information your support team can quickly identify whether the issue stems from naming, device configuration, or the upload pipeline.
