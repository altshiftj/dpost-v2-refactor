"""Guard against duplicate unit-test module basenames causing import mismatches."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


def test_unit_test_module_basenames_are_unique() -> None:
    """Prevent pytest import-name collisions across unit tests."""
    unit_root = Path(__file__).resolve().parent
    grouped: dict[str, list[Path]] = defaultdict(list)

    def _is_package_scoped(path: Path) -> bool:
        current = unit_root
        for part in path.relative_to(unit_root).parts[:-1]:
            current = current / part
            if not (current / "__init__.py").exists():
                return False
        return True

    def _import_key(path: Path) -> str:
        relative = path.relative_to(unit_root)
        if _is_package_scoped(path):
            return ".".join(relative.with_suffix("").parts)
        return path.stem

    for path in unit_root.rglob("test_*.py"):
        grouped[_import_key(path)].append(path)

    collisions = {
        name: sorted(str(path.relative_to(unit_root)) for path in paths)
        for name, paths in grouped.items()
        if len(paths) > 1
    }

    assert collisions == {}
