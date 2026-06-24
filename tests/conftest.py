"""Shared pytest configuration and import paths."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Several backend modules import sibling packages as top-level names
# (e.g. `from core.embedding import ...`).  Adding these directories to
# sys.path makes the test suite order-independent and robust.
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "core"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "agents"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "scripts"))
