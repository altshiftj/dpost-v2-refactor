"""Executable entry point that boots the Watchdog GUI application."""

import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from prometheus_client import start_http_server

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.observability import start_observability_server
from ipat_watchdog.core.app.device_watchdog_app import DeviceWatchdogApp
from ipat_watchdog.loader import load_device_plugin, load_pc_plugin, get_devices_for_pc
from ipat_watchdog.core.config import ConfigService, DeviceConfig, init_config
from ipat_watchdog.core.sync.sync_kadi import KadiSyncManager
from ipat_watchdog.core.ui.ui_tkinter import TKinterUI
from ipat_watchdog.core.ui.adapters import UiInteractionAdapter
from ipat_watchdog.core.storage.filesystem_utils import init_dirs

logger = setup_logger(__name__)

# ---------------------------
# Load only the bundled .env
# ---------------------------


def _bundle_dir() -> Path:
    """
    When frozen, PyInstaller unpacks datas into sys._MEIPASS.
    In dev, read from repo/build so behavior mirrors the exe.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # dev: src/ipat_watchdog/__main__.py ↩ up 3 ↩ repo root ↩ build/
    return Path(__file__).resolve().parents[3] / "build"


def _load_bundled_env() -> None:
    env_path = _bundle_dir() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        logger.info("Loaded bundled env: %s", env_path)
    else:
        logger.error("Bundled .env not found at %s", env_path)
        # keep running; _require_pc_name will enforce PC_NAME presence


# Load config before anything reads env vars
_load_bundled_env()

# ---------------------------
# Config resolution
# ---------------------------


def _split_list_env(value: str) -> List[str]:
    return [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]


def _require_pc_name() -> str:
    pc = os.getenv("PC_NAME", "").strip()
    if not pc:
        logger.error("PC_NAME must be set in bundled .env or environment.")
        sys.exit(1)
    return pc


def _resolve_device_names(pc_name: str) -> List[str]:
    explicit = _split_list_env(os.getenv("DEVICE_PLUGINS", ""))
    if explicit:
        logger.info("Using devices from DEVICE_PLUGINS: %s", explicit)
        return explicit
    inferred = get_devices_for_pc(pc_name)
    logger.info("No DEVICE_PLUGINS set; inferred from PC '%s': %s", pc_name, inferred)
    return inferred


def _load_configs(pc_name: str, device_names: List[str]) -> tuple[ConfigService, list[DeviceConfig]]:
    logger.info("Loading PC plugin: %s with devices: %s", pc_name, device_names)
    pc_plugin = load_pc_plugin(pc_name)
    pc_config = pc_plugin.get_config()

    device_configs: list[DeviceConfig] = []
    for dn in device_names:
        plugin = load_device_plugin(dn)
        device_configs.append(plugin.get_config())

    service = init_config(pc_config, device_configs)
    return service, device_configs


# ---------------------------
# App entry
# ---------------------------

PROMETHEUS_PORT = 8000
OBSERVABILITY_PORT = 8001


def main() -> None:
    try:
        pc_name = _require_pc_name()
    except SystemExit:
        # Fallback: prompt user for PC name if not set
        pc_name = "zwick_blb"
        if not pc_name:
            logger.error("PC_NAME is required.")
            sys.exit(1)

    # Allow device_names to be specified via env, fallback to prompt if not set/inferred
    device_names = _resolve_device_names(pc_name)
    if not device_names:
        # Hardcoded device names fallback
        device_names = ["utm_zwick"]  # Replace with your actual device names
        logger.warning("No devices found; using hardcoded list: %s", device_names)
        if not device_names:
            logger.error("At least one device name is required.")
            sys.exit(1)

    config_service, _ = _load_configs(pc_name, device_names)

    init_dirs()

    start_http_server(PROMETHEUS_PORT)
    logger.info("Prometheus metrics server started on port %d", PROMETHEUS_PORT)

    start_observability_server()
    logger.info("Observability server started on port %d", OBSERVABILITY_PORT)

    ui = TKinterUI()
    interaction_port = UiInteractionAdapter(ui)
    sync = KadiSyncManager(interactions=interaction_port)

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync,
        config_service=config_service,
    )
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception("Application failed to start: %s", exc)
        sys.exit(1)
