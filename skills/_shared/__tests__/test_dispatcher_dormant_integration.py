"""Phase 2a RED — sprint-4 (c) dispatcher-live-dormant-mode integration.

PROP-D1..D4 + PROP-E5-sentinel-idempotent + PROP-I2-no-tmux-kill.

These MUST fail until Phase 2b wires the dormant check into
proactive-loop-dispatch.py STEP between line 170 and line 195.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DISPATCH_PY = REPO_ROOT / "skills" / "_shared" / "proactive-loop-dispatch.py"
SHARED_DIR = REPO_ROOT / "skills" / "_shared"

DAY = 86400


def _menu(items: list[dict] | None = None, time_horizon_days: int | None = None) -> dict:
    menu = {"schema_version": 1,
            "categories": items or [{"name": "noop", "category": "noop",
                                     "roi_jpy_expected": 0, "min_cadence_seconds": 300}],
            "novelty_quota_ratio": 0.0}
    if time_horizon_days is not None:
        menu["time_horizon_days"] = time_horizon_days
    return menu


def _seed_slot(tmp_path: Path, slot_name: str, *,
               roi_rows: list[dict] | None = None,
               age_days: float = 100.0,
               menu: dict | None = None) -> Path:
    slot_dir = tmp_path / "loops" / slot_name
    slot_dir.mkdir(parents=True, exist_ok=True)
    (slot_dir / "menu.json").write_text(json.dumps(menu or _menu(time_horizon_days=14)))
    (slot_dir / "roi.jsonl").write_text(
        "\n".join(json.dumps(r) for r in (roi_rows or [])) + ("\n" if roi_rows else "")
    )
    (slot_dir / "build_log.md").write_text("")
    # Backdate slot_dir mtime to simulate age
    st_time = time.time() - age_days * DAY
    os.utime(slot_dir, (st_time, st_time))
    return slot_dir


def _run_dispatch(slot_dir: Path, home: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PYTHONPATH"] = str(SHARED_DIR)
    return subprocess.run(
        [sys.executable, str(DISPATCH_PY), "--slot", slot_dir.name,
         "--slot-dir", str(slot_dir), "--once"],
        env=env, capture_output=True, text=True, timeout=30,
    )


def test_D1_dispatcher_invokes_dormant_check_when_roi_exists(tmp_path):
    """PROP-D1: after menu load, the dormant check runs and writes sentinel
    when compute_dormant_state returns is_dormant=True."""
    now = int(time.time())
    # 45 negative-ROI days + 1 real settle 2d ago → live_mode=True, tail neg > 14
    rows = []
    for i in range(45):
        rows.append({"ts": now - (45 - i) * DAY, "pass_id": f"p-{i}",
                     "roi_jpy_realized": 0, "roi_jpy_expected": 500,
                     "outcome": "did-nothing"})
    rows.append({"ts": now - 2 * DAY, "pass_id": "p-settle",
                 "roi_jpy_realized": 25000, "roi_jpy_expected": 0,
                 "outcome": "settle:seeded"})
    slot_dir = _seed_slot(tmp_path, "gig", roi_rows=rows, age_days=100.0,
                          menu=_menu(time_horizon_days=14))
    result = _run_dispatch(slot_dir, tmp_path)
    assert result.returncode == 0, result.stderr
    # PROP-D2: sentinel written on this tick (evidence in stderr / file exists)
    sentinel = slot_dir / ".dormant.sentinel"
    assert sentinel.exists(), f"expected .dormant.sentinel; stderr={result.stderr}"
    ev = json.loads(sentinel.read_text())
    assert ev.get("live_mode") is True
    assert int(ev.get("consecutive_neg_windows", 0)) > 14
    assert ev.get("window_days") == 90


def test_D1_no_sentinel_when_no_realized(tmp_path):
    """PROP-D1 negative: live_mode=False → NEVER write sentinel."""
    now = int(time.time())
    rows = [{"ts": now - i * DAY, "pass_id": f"p-{i}",
             "roi_jpy_realized": 0, "roi_jpy_expected": 500,
             "outcome": "did-nothing"}
            for i in range(1, 60)]
    slot_dir = _seed_slot(tmp_path, "gig", roi_rows=rows, age_days=100.0,
                          menu=_menu(time_horizon_days=14))
    _run_dispatch(slot_dir, tmp_path)
    assert not (slot_dir / ".dormant.sentinel").exists()


def test_E5_sentinel_idempotent(tmp_path):
    """PROP-E5: existing sentinel is NEVER overwritten."""
    now = int(time.time())
    rows = []
    for i in range(45):
        rows.append({"ts": now - (45 - i) * DAY, "pass_id": f"p-{i}",
                     "roi_jpy_realized": 0, "roi_jpy_expected": 500,
                     "outcome": "did-nothing"})
    rows.append({"ts": now - 2 * DAY, "pass_id": "p-settle",
                 "roi_jpy_realized": 25000, "roi_jpy_expected": 0,
                 "outcome": "settle:seeded"})
    slot_dir = _seed_slot(tmp_path, "gig", roi_rows=rows, age_days=100.0,
                          menu=_menu(time_horizon_days=14))
    sentinel = slot_dir / ".dormant.sentinel"
    sentinel.write_text('{"marker": "pre-existing"}')
    _run_dispatch(slot_dir, tmp_path)
    ev = json.loads(sentinel.read_text())
    assert ev.get("marker") == "pre-existing", "sentinel was overwritten"


def test_D3_dispatcher_never_removes_sentinel(tmp_path):
    """PROP-D3: grep dispatcher for `.dormant.sentinel` deletion = 0.
    """
    src = DISPATCH_PY.read_text()
    # No `Path.unlink` or `os.remove` operating on `.dormant.sentinel`
    for pat in [r"\.dormant\.sentinel.*\.unlink", r"remove.*\.dormant\.sentinel",
                r"unlink.*\.dormant\.sentinel"]:
        assert re.search(pat, src) is None, f"dispatcher removes sentinel: {pat}"


def test_D4_fail_closed_on_read_error(tmp_path):
    """PROP-D4: If roi.jsonl is unreadable, dispatcher logs and CONTINUES
    without writing a sentinel."""
    slot_dir = _seed_slot(tmp_path, "gig", roi_rows=[], age_days=100.0)
    # Corrupt roi.jsonl → OSError on open
    (slot_dir / "roi.jsonl").unlink()
    (slot_dir / "roi.jsonl").mkdir()  # dir named roi.jsonl → open() raises
    result = _run_dispatch(slot_dir, tmp_path)
    assert result.returncode == 0, result.stderr
    assert not (slot_dir / ".dormant.sentinel").exists()


def test_I2_no_tmux_kill_referenced_in_dormant_wire(tmp_path):
    """PROP-I2 (INV-1): the dormant wire code path MUST NOT reference tmux kill.
    Grep the source region for any subprocess of tmux kill-session.
    """
    src = DISPATCH_PY.read_text()
    assert "kill-session" not in src, "dispatcher must never kill tmux"
