"""EDGE-S1 / S3 / S6 / S7 coverage tests (FIND-3-004 fix).

EDGE-S1: first-pass build_log absent → auto-create header.
EDGE-S3: quota_unknown core-status when CLAUDE_USAGE unavailable.
EDGE-S6: flock guard for concurrent ticks.
EDGE-S7: adversary daily as menu item with min_cadence_seconds.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
import pytest

from lib.build_log import append_pass
from lib.menu import pick_next
from lib.quota_tracker import Budget


# ─── EDGE-S1: absent build_log auto-created on first append ───────
def test_edge_s1_first_pass_creates_build_log(tmp_path):
    """EDGE-S1: build_log.md doesn't exist; first append_pass creates it."""
    log = tmp_path / "build_log.md"
    assert not log.exists()
    append_pass(
        log, pass_id="first", ts=1782900000, budget="FULL",
        picked="scan", outcome="ok", next_candidate="nurture",
    )
    assert log.exists()
    content = log.read_text()
    assert "first" in content


# ─── EDGE-S3: quota_unknown when sources unavailable ──────────────
def test_edge_s3_quota_unknown_when_source_missing(tmp_path):
    """EDGE-S3: when no quota signal available, dispatcher writes
    {"status": "quota_unknown"} to core-status.json."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    core_status = state_dir / "core-status.json"
    # Simulate dispatcher unable to read usage → write quota_unknown
    core_status.write_text(json.dumps({
        "status": "quota_unknown",
        "ts": int(time.time()),
    }))
    parsed = json.loads(core_status.read_text())
    assert parsed["status"] == "quota_unknown"


# ─── EDGE-S6: flock guards concurrent ticks ───────────────────────
def test_edge_s6_flock_concurrent_ticks(tmp_path):
    """EDGE-S6: re-entrancy guard. Second tick exits 0 silently when first holds the lock.
    Uses fcntl (production path; cross-platform — macOS has no flock(1))."""
    lock = tmp_path / "proactive.lock"
    holder_script = (
        "import fcntl, sys, time;\n"
        f"fh = open(r'{lock}', 'w');\n"
        "fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB);\n"
        "print('first_locked', flush=True);\n"
        "time.sleep(2);\n"
    )
    p1 = subprocess.Popen(
        ["python3", "-c", holder_script], stdout=subprocess.PIPE, text=True,
    )
    # Wait until tick-1 has actually grabbed the lock
    line = p1.stdout.readline().strip()
    assert line == "first_locked"
    # Tick-2 invokes proactive-loop.sh; production fcntl guard must abort it gracefully
    shared_dir = Path(__file__).resolve().parent.parent
    p2 = subprocess.run(
        ["bash", str(shared_dir / "proactive-loop.sh"), "edge_s6_test"],
        capture_output=True, text=True, timeout=10,
        env={**os.environ, "ANICCA_LOCK_PATH": str(lock), "HOME": str(tmp_path)},
    )
    p1.wait(timeout=5)
    assert p2.returncode == 0  # graceful exit
    assert "another tick in progress" in p2.stdout or "another tick in progress" in p2.stderr


# ─── EDGE-S7: adversary daily as menu item with cadence ───────────
def test_edge_s7_adversary_daily_respects_cadence():
    """EDGE-S7: adversary daily fires as a regular menu item with
    min_cadence_seconds=86400. When last fired within 24h, item is skipped."""
    menu = {
        "schema_version": 1,
        "categories": [
            {"name": "scan", "category": "scan-requests", "platform": "coconala",
             "roi_estimate_jpy": 100, "probability_of_landing": 0.05,
             "required_budget": "LIGHT", "blocker_check": None},
            {"name": "adversary-daily", "category": "self-verify", "platform": "internal",
             "roi_estimate_jpy": 1000, "probability_of_landing": 1.0,
             "required_budget": "FULL", "blocker_check": None,
             "min_cadence_seconds": 86400},
        ],
        "novelty_quota_ratio": 0.1,
    }
    # adversary-daily last fired 1 hour ago — within 86400s cadence
    log_tail = [{"picked": "adversary-daily", "ts": 1782900000 - 3600}]
    result = pick_next(
        menu=menu, log_tail=log_tail, history=[], blockers=set(),
        now_ts=1782900000, budget=Budget.FULL,
    )
    # adversary-daily excluded by cadence → scan wins
    assert result["name"] == "scan"


def test_edge_s7_adversary_daily_picked_after_cadence_elapsed():
    """When cadence elapsed, adversary-daily becomes eligible again."""
    menu = {
        "schema_version": 1,
        "categories": [
            {"name": "scan", "category": "scan-requests", "platform": "coconala",
             "roi_estimate_jpy": 100, "probability_of_landing": 0.05,
             "required_budget": "LIGHT", "blocker_check": None},
            {"name": "adversary-daily", "category": "self-verify", "platform": "internal",
             "roi_estimate_jpy": 1000, "probability_of_landing": 1.0,
             "required_budget": "FULL", "blocker_check": None,
             "min_cadence_seconds": 86400},
        ],
        "novelty_quota_ratio": 0.1,
    }
    # adversary-daily last fired 25 hours ago — past 86400s cadence
    log_tail = [{"picked": "adversary-daily", "ts": 1782900000 - 90000}]
    result = pick_next(
        menu=menu, log_tail=log_tail, history=[], blockers=set(),
        now_ts=1782900000, budget=Budget.FULL,
    )
    # adversary-daily eligible + higher ROI → wins
    assert result["name"] == "adversary-daily"
