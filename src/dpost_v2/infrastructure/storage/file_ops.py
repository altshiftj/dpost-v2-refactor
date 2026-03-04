"""Concrete filesystem adapter with root-scoped safety checks."""

from __future__ import annotations

import errno
import shutil
from pathlib import Path


class FileOpsError(RuntimeError):
    """Base error for filesystem adapter failures."""


class FileOpsPathSafetyError(FileOpsError):
    """Raised when requested path escapes configured adapter root."""


class FileOpsNotFoundError(FileOpsError):
    """Raised when required source paths are missing."""


class FileOpsPermissionError(FileOpsError):
    """Raised when filesystem permissions prevent an operation."""


class FileOpsLockedError(FileOpsError):
    """Raised when operation fails due to lock/busy state."""


class FileOpsCrossDeviceError(FileOpsError):
    """Raised when cross-device move fallback fails."""


class LocalFileOpsAdapter:
    """Root-scoped implementation of file operations contract."""

    def __init__(self, root: str | Path, *, safe_noop: bool = True) -> None:
        self._root = Path(root).expanduser().resolve()
        self._safe_noop = bool(safe_noop)

    def read_bytes(self, path: str) -> bytes:
        """Read file bytes for a root-safe path."""
        target = self._resolve_scoped_path(path)
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise FileOpsNotFoundError(f"Source path not found: {target}") from exc
        except PermissionError as exc:
            raise FileOpsPermissionError(f"Permission denied for {target}") from exc
        except BlockingIOError as exc:
            raise FileOpsLockedError(f"Source path is locked: {target}") from exc

    def move(self, source: str, target: str) -> Path:
        """Move a source path to a target path within root scope."""
        source_path = self._resolve_scoped_path(source)
        target_path = self._resolve_scoped_path(target)
        if not source_path.exists():
            raise FileOpsNotFoundError(f"Source path not found: {source_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            return source_path.rename(target_path)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                try:
                    moved = shutil.move(str(source_path), str(target_path))
                    return Path(moved)
                except Exception as fallback_exc:  # noqa: BLE001
                    raise FileOpsCrossDeviceError(
                        f"Cross-device move failed for {source_path} -> {target_path}"
                    ) from fallback_exc
            raise self._map_os_error(exc, operation="move")

    def exists(self, path: str) -> bool:
        """Return whether root-safe path currently exists."""
        return self._resolve_scoped_path(path).exists()

    def mkdir(self, path: str) -> Path:
        """Create root-safe directory path if missing."""
        target = self._resolve_scoped_path(path)
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except OSError as exc:
            raise self._map_os_error(exc, operation="mkdir")

    def delete(self, path: str) -> None:
        """Delete file or directory path with optional safe no-op semantics."""
        target = self._resolve_scoped_path(path)
        if not target.exists():
            if self._safe_noop:
                return
            raise FileOpsNotFoundError(f"Delete target not found: {target}")

        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        except OSError as exc:
            raise self._map_os_error(exc, operation="delete")

    def _resolve_scoped_path(self, raw_path: str) -> Path:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise FileOpsPathSafetyError("path must be a non-empty string")

        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = self._root / candidate
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise FileOpsPathSafetyError(
                f"path escapes adapter root scope: {resolved}"
            ) from exc
        return resolved

    @staticmethod
    def _map_os_error(exc: OSError, *, operation: str) -> FileOpsError:
        if isinstance(exc, PermissionError):
            return FileOpsPermissionError(f"{operation} failed: {exc}")
        if isinstance(exc, BlockingIOError):
            return FileOpsLockedError(f"{operation} failed: {exc}")
        return FileOpsError(f"{operation} failed: {exc}")
