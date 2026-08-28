from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("application_direct_evidence_budget", SCRIPTS / "application_direct.py")
assert SPEC and SPEC.loader
application_direct = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_direct)


def test_apply_evidence_budget_leaves_host_cleanup_headroom() -> None:
    assert application_direct.APPLY_EVIDENCE_HIGH_WATER_BYTES == 400 * 1024 * 1024
    assert application_direct.APPLY_EVIDENCE_LOW_WATER_BYTES == 250 * 1024 * 1024

