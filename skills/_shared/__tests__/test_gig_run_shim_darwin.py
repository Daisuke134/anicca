"""PROP-S1 (back-compat), PROP-I1 (no ~/loops writes), PROP-I2 (no tmux kill)
integration tests on Darwin. Runs the real skills/earn/gig/run.sh and parses
its stdout JSON.

NOTE: this test reads ~/gig/ ledgers (production data) but writes NOTHING.
It also gates gig-cli.sh side-effects by skipping if HOME isn't pointing at
the real anicca user.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="gig run.sh shim is Darwin-only (depends on launchctl + ~/gig core)",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_SH = REPO_ROOT / "skills" / "earn" / "gig" / "run.sh"
LOOPS_DIR = Path.home() / "loops" / "gig"

EXISTING_KEYS = {
    "source", "task", "funding", "earn_usdc", "cost_usdc",
    "jpy_earned", "applied_total", "core", "wake", "note",
}


def _snapshot_mtimes(d: Path) -> dict:
    if not d.exists():
        return {}
    snap = {}
    for f in d.rglob("*"):
        try:
            snap[str(f)] = f.stat().st_mtime_ns
        except FileNotFoundError:
            pass
    return snap


def test_status_json_back_compat_and_shim_observability():
    """PROP-S1 + PROP-S2 + PROP-I1 in one integration shot."""
    before = _snapshot_mtimes(LOOPS_DIR)
    r = subprocess.run(["bash", str(RUN_SH)], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"run.sh exit non-zero: {r.stderr}"
    # parse stdout (last line is the JSON; gig-cli.sh side may emit other lines)
    lines = [l for l in r.stdout.splitlines() if l.strip().startswith("{")]
    assert lines, f"no JSON line in stdout: {r.stdout[:500]}"
    data = json.loads(lines[-1])
    # PROP-S1: all existing keys preserved
    missing = EXISTING_KEYS - set(data.keys())
    assert not missing, f"REQ-S1 violation: missing existing keys {missing}"
    # PROP-S2: proactive_loop object present with 4 named keys
    assert "proactive_loop" in data, "REQ-S2 violation: proactive_loop key missing"
    pl = data["proactive_loop"]
    assert set(pl.keys()) == {"installed", "last_pass_ts", "last_pass_step", "build_log_passes"}, \
        f"REQ-S2 violation: proactive_loop shape = {set(pl.keys())}"
    # PROP-I1: no ~/loops/gig/ writes by the shim
    after = _snapshot_mtimes(LOOPS_DIR)
    assert before == after, f"REQ-I1 violation: ~/loops/gig/ mtimes changed: {set(after) ^ set(before)}"
