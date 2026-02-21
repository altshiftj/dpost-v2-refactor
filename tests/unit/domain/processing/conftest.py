"""Shared local fixtures for domain processing unit tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture
def local_tmp_path() -> Iterator[Path]:
    """Provide a writable temp folder without relying on pytest tmp_path."""
    root = Path(".dpost_test_tmp")
    root.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=root) as tmp_dir:
        yield Path(tmp_dir)
