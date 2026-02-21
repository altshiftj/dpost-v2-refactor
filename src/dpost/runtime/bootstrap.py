"""Native runtime bootstrap service and contracts for dpost startup paths."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from dotenv import load_dotenv
from prometheus_client import start_http_server

from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.runtime import bootstrap_dependencies
from dpost.plugins.loading import get_devices_for_pc

try:
    from dpost.infrastructure.observability import start_observability_server
except ModuleNotFoundError as _obs_exc:
    start_observability_server = None
    _OBSERVABILITY_IMPORT_ERROR = _obs_exc
else:
    _OBSERVABILITY_IMPORT_ERROR = None

logger = setup_logger(__name__)

DEFAULT_PROMETHEUS_PORT = 8000
DEFAULT_OBSERVABILITY_PORT = 8001

UiInteractionAdapter = bootstrap_dependencies.UiInteractionAdapter
UiTaskScheduler = bootstrap_dependencies.UiTaskScheduler
DeviceWatchdogApp = bootstrap_dependencies.DeviceWatchdogApp
init_dirs = bootstrap_dependencies.init_runtime_dirs
_build_config_service = bootstrap_dependencies.build_config_service


class StartupError(RuntimeError):
    """Raised when runtime bootstrap configuration fails."""


class MissingConfiguration(StartupError):
    """Raised when required environment configuration is missing."""


@dataclass(frozen=True)
class StartupSettings:
    """Resolved startup settings for dpost runtime bootstrap."""

    pc_name: str
    device_names: tuple[str, ...]
    prometheus_port: int = DEFAULT_PROMETHEUS_PORT
    observability_port: int = DEFAULT_OBSERVABILITY_PORT
    env_source: Path | None = None


@dataclass
class BootstrapContext:
    """Concrete artifacts returned by runtime bootstrap for entrypoint use."""

    settings: StartupSettings
    config_service: object
    app: object
    ui: object
    sync_manager: object
    interactions: object
    scheduler: object


def bootstrap(
    settings: StartupSettings | None = None,
    *,
    ui_factory: Callable[[], object] = bootstrap_dependencies.default_ui_factory,
    sync_manager_factory: Callable[[object], object] = (
        bootstrap_dependencies.default_sync_manager_factory
    ),
) -> BootstrapContext:
    """Initialise config, services, and app runtime stack for dpost startup."""

    resolved = settings or collect_startup_settings()
    logger.info(
        "Starting dpost with PC=%s, devices=%s",
        resolved.pc_name,
        ", ".join(resolved.device_names),
    )

    config_service = _build_config_service(resolved.pc_name, resolved.device_names)
    init_dirs()

    start_http_server(resolved.prometheus_port)
    logger.info(
        "Prometheus metrics server listening on port %d", resolved.prometheus_port
    )

    if start_observability_server is not None:
        start_observability_server(port=resolved.observability_port)
        logger.info(
            "Observability server listening on port %d", resolved.observability_port
        )
    elif _OBSERVABILITY_IMPORT_ERROR is not None:
        logger.warning("Observability server disabled: %s", _OBSERVABILITY_IMPORT_ERROR)

    ui = ui_factory()
    interaction_adapter = UiInteractionAdapter(ui)
    scheduler = UiTaskScheduler(ui)
    sync_manager = sync_manager_factory(interaction_adapter)

    app = DeviceWatchdogApp(
        ui=ui,
        sync_manager=sync_manager,
        config_service=config_service,
        interactions=interaction_adapter,
        scheduler=scheduler,
    )

    return BootstrapContext(
        settings=resolved,
        config_service=config_service,
        app=app,
        ui=ui,
        sync_manager=sync_manager,
        interactions=interaction_adapter,
        scheduler=scheduler,
    )


def bootstrap_runtime(**kwargs: object) -> BootstrapContext:
    """Build and return a runtime context from startup wiring arguments."""
    return bootstrap(**kwargs)


def collect_startup_settings(
    *,
    pc_name: str | None = None,
    device_names: Sequence[str] | None = None,
    load_env: bool = True,
) -> StartupSettings:
    """Resolve startup settings from env vars and plugin metadata."""

    env_source = load_bundled_env() if load_env else None

    resolved_pc_name = (pc_name or os.getenv("PC_NAME", "")).strip()
    if not resolved_pc_name:
        raise MissingConfiguration("PC_NAME must be provided via environment or args.")

    resolved_device_names = tuple(
        device_names or _list_from_env(os.getenv("DEVICE_PLUGINS", ""))
    )
    if not resolved_device_names:
        resolved_device_names = tuple(get_devices_for_pc(resolved_pc_name))
        if not resolved_device_names:
            raise MissingConfiguration(
                "No device plugins were resolved. Set DEVICE_PLUGINS or configure the "
                "PC plugin."
            )

    prometheus_port = _coerce_port(
        os.getenv("PROMETHEUS_PORT"), DEFAULT_PROMETHEUS_PORT, "PROMETHEUS_PORT"
    )
    observability_port = _coerce_port(
        os.getenv("OBSERVABILITY_PORT"),
        DEFAULT_OBSERVABILITY_PORT,
        "OBSERVABILITY_PORT",
    )

    return StartupSettings(
        pc_name=resolved_pc_name,
        device_names=resolved_device_names,
        prometheus_port=prometheus_port,
        observability_port=observability_port,
        env_source=env_source,
    )


def build_startup_settings(**kwargs: object) -> StartupSettings:
    """Construct startup settings using the dpost runtime contract class."""
    return StartupSettings(**kwargs)


def startup_error(message: str) -> StartupError:
    """Create a startup error instance for composition/runtime contracts."""
    return StartupError(message)


def load_bundled_env(bundle_dir: Path | None = None) -> Path | None:
    """Load a bundled `.env` file when present."""

    env_dir = bundle_dir or _resolve_bundle_dir()
    env_path = env_dir / ".env"
    if not env_path.exists():
        logger.debug("No bundled .env file found at %s", env_path)
        return None

    load_dotenv(env_path, override=False)
    logger.info("Loaded environment from %s", env_path)
    return env_path


def _resolve_bundle_dir() -> Path:
    """Resolve the bundle directory for frozen/non-frozen runtime packaging."""
    if bool(getattr(sys, "frozen", False)):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)

    module_path = Path(__file__).resolve()
    try:
        return module_path.parents[4] / "build"
    except IndexError:
        return module_path.parent


def _list_from_env(raw: str) -> list[str]:
    return [
        token.strip() for token in raw.replace(";", ",").split(",") if token.strip()
    ]


def _coerce_port(raw: str | None, default: int, name: str) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise StartupError(f"Invalid integer value for {name}: {raw!r}") from exc
    if value <= 0:
        raise StartupError(f"{name} must be a positive integer. Got {value}.")
    return value


__all__ = [
    "BootstrapContext",
    "MissingConfiguration",
    "StartupError",
    "StartupSettings",
    "bootstrap",
    "bootstrap_runtime",
    "build_startup_settings",
    "collect_startup_settings",
    "startup_error",
]
