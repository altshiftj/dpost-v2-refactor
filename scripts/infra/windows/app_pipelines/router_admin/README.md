# Router/Admin Deployment Pipeline (Tunnel Mode)

## Overview
This folder contains a router-mediated deployment pipeline for the IPAT Watchdog Windows executables.  The scripts assume you reach a Windows target PC through a Linux router (jump host) by opening an SSH tunnel, and they orchestrate every stage from local testing to post-deploy health verification.

The entry point is `full_pipeline.ps1`, which executes the numbered stage scripts in order:

| Stage | Script | Purpose | Key tools & artifacts |
| --- | --- | --- | --- |
| 0 | `00-env.ps1` | Discovers the repo root, preloads Git metadata, prepares Pip extras, and exposes tunnel helpers plus router/PC credentials. | PowerShell, Git, PuTTY (`plink.exe`, `pscp.exe`), credential files under `%USERPROFILE%\.secure`. |
| 1 | `01-test.ps1` | Creates a disposable venv, installs project extras (CI + device plugins), ensures `build/.env`, and runs `pytest`. | Python ≥3.11, `pytest`, repo tests. |
| 2 | `02-build.ps1` | Builds the Windows executable with PyInstaller using the device-specific spec file and writes `build/version-<pc>.txt`. | PyInstaller, `build/specs/<pc>.spec`, `dist/wd-<pc>.exe`. |
| 3 | `03-sign.ps1` | Signs the freshly built executable with the configured PFX certificate and verifies the signature. | Windows SDK `signtool.exe`, `%USERPROFILE%\.secure\pfxpass.txt`. |
| 4 | `04-deploy.ps1` | Establishes the SSH tunnel, stops remote tasks, pushes the new binary and `version-<pc>.txt`, and verifies remote artifacts. | PuTTY (`plink`, `pscp`), Windows Scheduled Tasks, remote `C:\Watchdog`. |
| 5 | `05-run.ps1` | Registers/starts the `IPAT-Watchdog-<pc>` scheduled task on the target PC through the tunnel. | Inline PowerShell (EncodedCommand) using the Scheduled Tasks API. |
| 6 | `06-health_check.ps1` | Forwards local port → router → target and polls the watchdog HTTP health endpoint until success or timeout. | `Invoke-RestMethod` against `http://127.0.0.1:<localPort>/health`. |
| 7 | `07-rollback.ps1` | Restores `_backup` artifacts, restarts the scheduled task, and prints the recovered version info via the router hop. | Tunnel helpers, remote backups (`*_backup.*`). |

## Prerequisites
- Windows PowerShell 5.1+ or PowerShell 7 with access to Git, Python, and the Windows SDK signing tools.
- Python virtual environment tooling (`python -m venv`).
- PuTTY command-line utilities (`plink.exe`, `pscp.exe`) available on `PATH`.
- Access to the router and target PC using the credentials and host keys referenced in `00-env.ps1`.
- `%USERPROFILE%\.secure` directory containing:
  - `ipat_wd.pfx` signing certificate and `pfxpass.txt` password file.
  - Router/target password files named per `CI_JOB_NAME` (if password auth is used) **or** PuTTY `.ppk` keys plus a note of the matching passphrase.
  - Text files that record the trusted host key fingerprints you collect in the preparation steps below.
- A valid PyInstaller spec in `build/specs/<CI_JOB_NAME>.spec`.

## Preparing a new router/target pair
The pipeline assumes password-less SSH with known host fingerprints. Run through these steps once per new deployment device:

1. **Gather connection facts**
   - Confirm the router IP/port and username (`ROUTER_IP`, `ROUTER_PORT`, `ROUTER_USER`).
   - Confirm the Windows target IP/port/username (`TARGET_IP`, `TARGET_PORT`, `TARGET_USER`).
   - Decide on the `CI_JOB_NAME` and the list of `DEVICE_PLUGINS` you want enabled for that PC.

2. **Generate or reuse an SSH keypair**
   - On your workstation create an Ed25519 key (recommended):
     ```powershell
     ssh-keygen -t ed25519 -C "ipat-router-admin" -f $env:USERPROFILE\.ssh\id_ipat_router
     ```
   - Convert the private key to PuTTY format if you do not already have a `.ppk` version (PuTTYgen ▶ *Conversions* ▶ *Import key* ▶ *Save private key*).
   - Append the public key to the router's account:
     ```powershell
     type $env:USERPROFILE\.ssh\id_ipat_router.pub | ssh ipat@<router-ip> "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
     ```
   - Repeat for the Windows target account. One reliable flow is: copy the `.pub` file to the router (or straight to the target with `pscp`), then run a remote PowerShell command to append it to `%USERPROFILE%\.ssh\authorized_keys` for the service account.
   - Update `00-env.ps1` defaults or override at runtime so that `ROUTER_SSH_KEY` and `TARGET_SSH_KEY` point to the PuTTY `.ppk` you will use.

3. **Capture host key fingerprints**
   - From your workstation, capture the router's host key:
     ```powershell
     ssh-keyscan -t ed25519 <router-ip> | Set-Content $env:USERPROFILE\.secure\router_hostkey.pub
     ssh-keygen -lf $env:USERPROFILE\.secure\router_hostkey.pub
     ```
   - Capture the target host key through the router (to ensure you're seeing what the tunnel will trust):
     ```powershell
     ssh ipat@<router-ip> "ssh-keyscan -t ed25519 <target-ip>" | Set-Content $env:USERPROFILE\.secure\target_hostkey.pub
     ssh-keygen -lf $env:USERPROFILE\.secure\target_hostkey.pub
     ```
   - For PuTTY/Plink you can also use a one-off verbose connect to copy the SHA256 fingerprint:
     ```powershell
     plink.exe -ssh -v ipat@<router-ip>
     plink.exe -ssh -v -P 2222 horiba@127.0.0.1  # after starting a tunnel
     ```
   - Paste the resulting strings into `%USERPROFILE%\.secure\router_hostkey.txt` and `target_hostkey.txt`, then set `ROUTER_SSH_HOSTKEY` / `TARGET_SSH_HOSTKEY` to match (either by editing the environment or exporting per session).

4. **Prepare the `.secure` folder**
   - Copy the PuTTY `.ppk`, any required passphrase files, and the host-key text files into `%USERPROFILE%\.secure` with names that match the defaults in `00-env.ps1` (or adjust the env vars).
   - Ensure file permissions restrict read access to your user only.

5. **First tunnel smoke-test**
   - Dot-source `00-env.ps1`, run `Start-TargetTunnel`, then `Invoke-TargetCommand "hostname"` to confirm both jumps succeed without typing passwords.
   - Stop the tunnel (`Stop-Process -Name plink` or rerun `Stop-TargetTunnel`) once the verification succeeds.

Documenting the key fingerprints and `.ppk` locations now saves time when the pipeline scripts prompt for trusted hosts or try to reuse credentials during automated runs.

> **Tip:** You can override defaults (job name, device plugins, router IP, etc.) by exporting environment variables before running any stage. `00-env.ps1` composes the effective configuration and echoes the values for easy auditing.

## Running the full pipeline
```powershell
# From scripts\infra\windows\app_pipelines\router_admin
powershell -ExecutionPolicy Bypass -File .\full_pipeline.ps1
```

Flags allow you to skip individual stages or keep the pipeline running after a failure:

- `-SkipTest`, `-SkipBuild`, `-SkipSign`, `-SkipDeploy`, `-SkipRun`, `-SkipHealth`
- `-ContinueOnError` to collect results for every stage even if one fails

Example:
```powershell
powershell -ExecutionPolicy Bypass -File .\full_pipeline.ps1 -SkipSign -SkipHealth
```

## Running individual stages
Each numbered script can be executed on its own. Make sure `00-env.ps1` is dot-sourced first so that the shared helpers (`Start-TargetTunnel`, `Invoke-TargetCommand`, etc.) and environment variables are available.

```powershell
# Re-run only the build and deploy stages
powershell -ExecutionPolicy Bypass -Command ". .\00-env.ps1; .\02-build.ps1; .\04-deploy.ps1"
```

### Stage-specific notes
- **Testing (`01-test.ps1`)** writes a temporary venv named `.test_testvenv` and deletes any pre-existing copy.
- **Build (`02-build.ps1`)** expects the PyInstaller spec to exist; it writes `build/.env` and `build/version-<pc>.txt` before invoking PyInstaller.
- **Signing (`03-sign.ps1`)** exits early if `signtool.exe` is not available—install the Windows 10/11 SDK if needed.
- **Deploy (`04-deploy.ps1`)** rotates existing remote files to `_backup` variants and regenerates a job-aware `version-<pc>.txt` with deploy metadata (legacy `version.txt` is migrated automatically on first deploy).
- **Run (`05-run.ps1`)** registers/starts the Windows scheduled task via an inline, base64-encoded PowerShell script sent through the tunnel (no remote helper script required).
- **Health Check (`06-health_check.ps1`)** defaults to forwarding local port `18001` to `target:8001` and retries up to 30 times with a 5-second delay.
- **Rollback (`07-rollback.ps1`)** uses helper functions `Get-DoubleSSHCommand` and `Get-RouterSSHCommand`; ensure these are imported (for example from your shared router helper module) before invoking the script.

## Customising device plugins
`00-env.ps1` reads `CI_JOB_NAME` and `DEVICE_PLUGINS` to build the Pip extras string. Provide them ahead of time to tailor the build:

```powershell
$env:CI_JOB_NAME = "tischrem_blb"
$env:DEVICE_PLUGINS = "psa_horiba,dsv_horiba,utm_zwick"
powershell -ExecutionPolicy Bypass -File .\full_pipeline.ps1
```

This will install extras as `.[ci,build,tischrem_blb,psa_horiba,dsv_horiba,utm_zwick]` and produce `dist/wd-tischrem_blb.exe`.

## Health verification
`06-health_check.ps1` keeps the SSH tunnel open while it polls `http://127.0.0.1:<localPort>/health`. On success it prints the JSON response, elapsed time, and tears down the tunnel. On failure it exits with a non-zero status so CI surfaces the issue. Override `$env:TUN_PORT_1` if `18001` is already in use locally.

## Rollback workflow
Run `07-rollback.ps1` when a deployment needs to be reverted. The script:

1. Stops the `IPAT-Watchdog-<CI_JOB_NAME>` scheduled task and kills any running binary.
2. Copies `_backup` artifacts back into place (`wd-<pc>_backup.exe`, `version-<pc>_backup.txt`; falls back to legacy `version_backup.txt` if present).
3. Restarts the scheduled task and prints the restored version metadata.

A verification step lists the deployed files, shows their timestamps, and reports the task state. Review both the rollback and verification logs to confirm success.

## Troubleshooting
- **Missing PuTTY tools:** Install PuTTY or add the folder containing `plink.exe` and `pscp.exe` to `PATH`.
- **Git metadata warnings:** Ensure the scripts run within a Git clone; otherwise `00-env.ps1` will still work but omit commit information.
- **Spec file errors:** Confirm `build/specs/<CI_JOB_NAME>.spec` exists and is kept in sync with new dependencies.
- **Remote script not found:** No longer applies; `05-run.ps1` uses an inline registration script. If registration fails, check the remote `REMOTE_PATH` and the executable name.
- **Certificate load failure:** Check the `.secure` directory paths and that the password files contain Unicode strings convertible via `ConvertTo-SecureString`.

## Related documentation
- `docs/architecture/ProcessingPipeline.png` for a high-level visual of the watchdog processing pipeline.
- `PC_PLUGIN_README.md` for device-specific plugin information referenced by `DEVICE_PLUGINS`.

Keep this README alongside the scripts so operators and CI jobs share the same execution guide.
