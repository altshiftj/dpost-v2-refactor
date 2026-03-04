"""Shared pytest bootstrap for active test suites."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure tests import workspace sources, not a globally installed package.
TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"

for root in (SRC_ROOT, PROJECT_ROOT):
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
