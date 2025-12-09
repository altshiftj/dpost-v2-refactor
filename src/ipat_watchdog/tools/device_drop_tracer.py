"""Headless utility that records every filesystem change during a device run.

This tracer is meant for onboarding new instruments. It attaches a recursive
``watchdog`` observer to the configured watch directory, stores a rich timeline
of ``created/modified/moved/deleted`` events, and emits both a JSONL trace and
aggregated burst summaries. The resulting artefacts can be inspected to fine
‑tune :class:`WatcherSettings`, sentinel expectations, and plugin behaviour
before touching the main processing pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, MutableSequence, Sequence

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ipat_watchdog.core.app.bootstrap import collect_startup_settings
from ipat_watchdog.core.config import ConfigService, DeviceConfig, PCConfig, init_config
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.storage.filesystem_utils import init_dirs
from ipat_watchdog.loader import load_device_plugin, load_pc_plugin

logger = setup_logger(__name__)

TraceList = MutableSequence["TraceEvent"]


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Single filesystem event captured by the tracer."""

    timestamp: datetime
    event: str
    absolute_path: str
    relative_path: str
    parent: str
    depth: int
    is_directory: bool
    exists_after: bool
    size_bytes: int | None
    content_hash: str | None
    destination_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event": self.event,
            "absolute_path": self.absolute_path,
            "relative_path": self.relative_path,
            "parent": self.parent,
            "depth": self.depth,
            "is_directory": self.is_directory,
            "exists_after": self.exists_after,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "destination_path": self.destination_path,
        }


@dataclass(frozen=True, slots=True)
class BurstSummary:
    """Describes a burst of device IO (contiguous events separated by silence)."""

    index: int
    start: datetime
    end: datetime
    duration_seconds: float
    event_count: int
    depth_max: int
    event_breakdown: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_seconds": self.duration_seconds,
            "event_count": self.event_count,
            "depth_max": self.depth_max,
            "event_breakdown": self.event_breakdown,
        }


class _TracingEventHandler(FileSystemEventHandler):
    """Forwards every interesting filesystem event into the tracer pipeline."""

    def __init__(self, tracer: "DeviceDropTracer") -> None:
        super().__init__()
        self._tracer = tracer

    def on_created(self, event: FileSystemEvent) -> None:
        self._tracer.record("created", event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._tracer.record("modified", event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._tracer.record("deleted", event)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._tracer.record("moved", event)


class DeviceDropTracer:
    """Coordinates the watchdog observer and accumulates trace events."""

    def __init__(
        self,
        watch_dir: Path,
        *,
        silence_gap_seconds: float = 1.5,
        hash_threshold_bytes: int = 256 * 1024,
        echo_events: bool = True,
    ) -> None:
        self.watch_dir = watch_dir
        self.silence_gap = timedelta(seconds=max(silence_gap_seconds, 0.1))
        self.hash_threshold_bytes = max(hash_threshold_bytes, 0)
        self.echo_events = echo_events

        self.events: TraceList = []
        self._lock = threading.Lock()
        self._observer: Observer | None = None
        self._handler = _TracingEventHandler(self)
        self._start_time = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._observer is not None:
            return

        logger.info("Starting recursive observer for %s", self.watch_dir)
        observer = Observer()
        observer.schedule(self._handler, path=str(self.watch_dir), recursive=True)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        observer = self._observer
        if observer is None:
            return
        logger.info("Stopping observer...")
        observer.stop()
        observer.join()
        self._observer = None

    # ------------------------------------------------------------------ #
    # Event ingestion
    # ------------------------------------------------------------------ #
    def record(self, event_type: str, event: FileSystemEvent) -> None:
        timestamp = datetime.now(timezone.utc)
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path) if getattr(event, "dest_path", None) else None

        snapshot_path = dest_path if event_type == "moved" and dest_path else src_path
        exists_after = snapshot_path.exists()
        is_directory = event.is_directory
        size_bytes, content_hash = self._snapshot_file(snapshot_path, exists_after, is_directory)

        relative_path = self._relative(src_path)
        parent_rel = str(Path(relative_path).parent) if relative_path else "."

        depth = max(len(Path(relative_path).parts), 0)

        trace_event = TraceEvent(
            timestamp=timestamp,
            event=event_type,
            absolute_path=str(src_path),
            relative_path=relative_path,
            parent=parent_rel,
            depth=depth,
            is_directory=is_directory,
            exists_after=exists_after,
            size_bytes=size_bytes,
            content_hash=content_hash,
            destination_path=str(dest_path) if dest_path else None,
        )

        with self._lock:
            self.events.append(trace_event)

        if self.echo_events:
            self._echo_event(trace_event)

    def _snapshot_file(
        self,
        path: Path,
        exists_after: bool,
        is_directory: bool,
    ) -> tuple[int | None, str | None]:
        """Return (size, hash) for files when feasible."""
        if not exists_after or is_directory:
            return None, None
        try:
            stat = path.stat()
        except (FileNotFoundError, OSError):
            return None, None

        size = int(stat.st_size)
        if size == 0 or size > self.hash_threshold_bytes:
            return size, None

        try:
            data = path.read_bytes()
        except OSError:
            return size, None
        digest = hashlib.md5(data, usedforsecurity=False).hexdigest()
        return size, digest

    def _relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.watch_dir))
        except ValueError:
            return path.as_posix()

    def _echo_event(self, event: TraceEvent) -> None:
        human_path = event.relative_path or event.absolute_path
        hash_note = f" hash={event.content_hash}" if event.content_hash else ""
        size_note = f" size={event.size_bytes}" if event.size_bytes is not None else ""
        dest_note = f" -> {event.destination_path}" if event.destination_path else ""
        logger.info(
            "[%s] %s%s%s%s",
            event.timestamp.isoformat(),
            event.event.upper(),
            dest_note,
            f" {human_path}" if human_path else "",
            f"{size_note}{hash_note}",
        )

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def build_bursts(self) -> list[BurstSummary]:
        with self._lock:
            events = sorted(self.events, key=lambda item: item.timestamp)

        bursts: list[BurstSummary] = []

        if not events:
            return bursts

        idx = 1
        current: list[TraceEvent] = []

        for record in events:
            if not current:
                current.append(record)
                continue

            gap = record.timestamp - current[-1].timestamp
            if gap > self.silence_gap:
                bursts.append(self._collapse_burst(idx, current))
                idx += 1
                current = [record]
            else:
                current.append(record)

        if current:
            bursts.append(self._collapse_burst(idx, current))

        return bursts

    def _collapse_burst(self, index: int, records: list[TraceEvent]) -> BurstSummary:
        start = records[0].timestamp
        end = records[-1].timestamp
        duration = (end - start).total_seconds()
        breakdown = Counter(record.event for record in records)
        depth_max = max(record.depth for record in records)
        return BurstSummary(
            index=index,
            start=start,
            end=end,
            duration_seconds=duration,
            event_count=len(records),
            depth_max=depth_max,
            event_breakdown=dict(breakdown),
        )

    def write_reports(self, output_dir: Path | None) -> tuple[Path, Path]:
        events_copy: list[TraceEvent]
        with self._lock:
            events_copy = list(self.events)

        if not output_dir:
            output_dir = self.watch_dir / ".watchdog_traces"
        output_dir.mkdir(parents=True, exist_ok=True)

        slug = self._start_time.strftime("%Y%m%d-%H%M%S")
        trace_path = output_dir / f"trace_{slug}.jsonl"
        summary_path = output_dir / f"trace_{slug}_summary.json"

        logger.info("Writing %d events to %s", len(events_copy), trace_path)
        with trace_path.open("w", encoding="utf-8") as fh:
            for record in events_copy:
                fh.write(json.dumps(record.to_dict(), ensure_ascii=False))
                fh.write("\n")

        bursts = self.build_bursts()
        logger.info("Writing %d burst summaries to %s", len(bursts), summary_path)
        with summary_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "watch_dir": str(self.watch_dir),
                    "started": self._start_time.isoformat(),
                    "ended": datetime.now(timezone.utc).isoformat(),
                    "burst_gap_seconds": self.silence_gap.total_seconds(),
                    "bursts": [burst.to_dict() for burst in bursts],
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )

        return trace_path, summary_path


# ---------------------------------------------------------------------- #
# Bootstrapping helpers
# ---------------------------------------------------------------------- #
def _build_config_service(pc_config: PCConfig, device_configs: Iterable[DeviceConfig]) -> ConfigService:
    return init_config(pc_config, tuple(device_configs))


def _load_configs(pc_name: str, device_names: Sequence[str]) -> ConfigService:
    pc_plugin = load_pc_plugin(pc_name)
    device_configs = [load_device_plugin(name).get_config() for name in device_names]
    return _build_config_service(pc_plugin.get_config(), device_configs)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture recursive filesystem activity to inform WatcherSettings.",
    )
    parser.add_argument("--pc-name", help="Override PC plugin name (defaults to env/loader resolution).")
    parser.add_argument(
        "--device",
        dest="devices",
        action="append",
        help="Device plugin identifier to load (repeat for multiples). Defaults to DEVICE_PLUGINS.",
    )
    parser.add_argument(
        "--watch-dir",
        type=Path,
        help="Watch directory override. Defaults to the configured PC watch_dir.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Optional duration (seconds) to capture before stopping automatically.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Directory for the trace artefacts (default: <watch_dir>/.watchdog_traces).",
    )
    parser.add_argument(
        "--silence-gap",
        type=float,
        default=1.5,
        help="Seconds of inactivity that separate bursts (default: 1.5).",
    )
    parser.add_argument(
        "--hash-threshold",
        type=int,
        default=256 * 1024,
        help="Max file size (bytes) for inline MD5 hashing (default: 262144).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable console echo of every captured event.",
    )
    return parser.parse_args(argv)


def _resolve_config(args: argparse.Namespace) -> tuple[ConfigService | None, Path]:
    if args.watch_dir:
        return None, args.watch_dir.expanduser().resolve()

    settings = collect_startup_settings(pc_name=args.pc_name, device_names=args.devices)
    config_service = _load_configs(settings.pc_name, settings.device_names)
    init_dirs()
    return config_service, config_service.pc.paths.watch_dir


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    config_service, watch_dir = _resolve_config(args)
    watch_dir = watch_dir.expanduser().resolve()

    tracer = DeviceDropTracer(
        watch_dir=watch_dir,
        silence_gap_seconds=args.silence_gap,
        hash_threshold_bytes=args.hash_threshold,
        echo_events=not args.quiet,
    )

    logger.info("Tracing directory %s", watch_dir)
    tracer.start()

    try:
        if args.duration and args.duration > 0:
            logger.info("Capturing for %.1f seconds...", args.duration)
            time.sleep(args.duration)
        else:
            logger.info("Press Ctrl+C to stop recording.")
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user, flushing trace...")
    finally:
        tracer.stop()
        trace_path, summary_path = tracer.write_reports(args.output)
        logger.info("Trace saved to %s", trace_path)
        logger.info("Summary saved to %s", summary_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
