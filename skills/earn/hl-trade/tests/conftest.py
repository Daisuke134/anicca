"""Test scaffolding for hl-realized-pnl's PURE + IMPURE reconcile layer.

Puts `skills/earn/hl-trade/lib/` on sys.path so tests can `import fills` / `import reconcile`
directly (flat-module style, mirroring hl.py's own no-package convention — hl-trade has no
`lib/__init__.py` and this feature does not add one). Mirrors self-improve/tests/conftest.py's
sys.path-insert technique, pointed one level deeper (at lib/, not the skill root), since fills.py
and reconcile.py are plain top-level modules under lib/, not a `lib` package the tests import
through (`from lib import ...`).
"""
from __future__ import annotations

import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
HL_TRADE_DIR = os.path.dirname(TESTS_DIR)
LIB_DIR = os.path.join(HL_TRADE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
