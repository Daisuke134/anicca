"""pytest config — make `from lib import ...` work from the test dir.

Phase 2a RED phase: tests in this directory MUST fail because no lib module exists yet.
When lib/ files appear in Phase 2b, the imports resolve and tests start passing one by one.
"""
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SHARED))
