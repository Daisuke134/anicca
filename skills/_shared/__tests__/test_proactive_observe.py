"""PROP-S2..S5, PROP-I3, PROP-E2, PROP-E5 unit tests for lib.proactive_observe.

PURE helpers: summarize_loops_dir(loops_dir, plist_path, launchctl_print_rc).
Cross-platform. Phase 2a RED for gig-run-shim.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

# RED: this import must fail until lib/proactive_observe.py exists
from lib.proactive_observe import summarize_loops_dir


# ─── PROP-S2: result shape ─────────────────────────────────────────
def test_returns_4_named_keys(tmp_path):
    res = summarize_loops_dir(tmp_path, tmp_path / "plist.plist", launchctl_print_rc=1)
    assert set(res.keys()) == {"installed", "last_pass_ts", "last_pass_step", "build_log_passes"}


# ─── PROP-S3: BOTH disk AND launchctl rc=0 ─────────────────────────
def test_installed_requires_both_disk_and_rc_zero(tmp_path):
    loops = tmp_path / "loops"
    loops.mkdir()
    plist = tmp_path / "plist"
    # Case A: rc=0 but plist missing → False
    assert summarize_loops_dir(loops, plist, launchctl_print_rc=0)["installed"] is False
    # Case B: plist exists but rc!=0 → False (= EDGE-E5)
    plist.write_text("x")
    assert summarize_loops_dir(loops, plist, launchctl_print_rc=1)["installed"] is False
    # Case C: BOTH → True
    assert summarize_loops_dir(loops, plist, launchctl_print_rc=0)["installed"] is True


# ─── PROP-S4: core-status.json read ────────────────────────────────
def test_last_pass_ts_and_step_from_core_status(tmp_path):
    loops = tmp_path / "loops"
    state = loops / "state"
    state.mkdir(parents=True)
    (state / "core-status.json").write_text(json.dumps({
        "ts": 1782900000, "slot": "gig", "status": "idle", "step": "done",
    }))
    res = summarize_loops_dir(loops, tmp_path / "p", launchctl_print_rc=1)
    assert res["last_pass_ts"] == 1782900000
    assert res["last_pass_step"] == "done"


# ─── PROP-S5: count of '## ' headers ──────────────────────────────
def test_build_log_passes_counts_headers(tmp_path):
    loops = tmp_path / "loops"
    loops.mkdir()
    (loops / "build_log.md").write_text(
        "## 2026-07-01 — pass p-1\nbudget: MEDIUM\n\n"
        "## 2026-07-01 — pass p-2\nbudget: LIGHT\n\n"
        "## 2026-07-01 — pass p-3\nbudget: FULL\n"
    )
    res = summarize_loops_dir(loops, tmp_path / "p", launchctl_print_rc=1)
    assert res["build_log_passes"] == 3


def test_build_log_empty_returns_zero(tmp_path):
    loops = tmp_path / "loops"
    loops.mkdir()
    (loops / "build_log.md").write_text("")  # EDGE-E3
    res = summarize_loops_dir(loops, tmp_path / "p", launchctl_print_rc=1)
    assert res["build_log_passes"] == 0


# ─── PROP-I3: pre-migration graceful (loops dir absent) ───────────
def test_pre_migration_no_loops_dir(tmp_path):
    loops = tmp_path / "loops-not-exist"
    res = summarize_loops_dir(loops, tmp_path / "p", launchctl_print_rc=1)
    assert res == {
        "installed": False, "last_pass_ts": None,
        "last_pass_step": None, "build_log_passes": 0,
    }


# ─── PROP-E2: malformed JSON → null fields, no crash ──────────────
def test_malformed_core_status_no_crash(tmp_path):
    loops = tmp_path / "loops"
    state = loops / "state"
    state.mkdir(parents=True)
    (state / "core-status.json").write_text("{ not valid json")  # EDGE-E2
    res = summarize_loops_dir(loops, tmp_path / "p", launchctl_print_rc=1)
    assert res["last_pass_ts"] is None
    assert res["last_pass_step"] is None
    # other fields still computed
    assert res["installed"] is False
    assert res["build_log_passes"] == 0


# ─── PROP-S2: ALL fields present even on full-empty inputs ────────
def test_all_keys_always_present(tmp_path):
    # Cycle every input combination — all 4 keys must always be in dict
    for plist_rc in [0, 1]:
        for has_plist in [True, False]:
            plist = tmp_path / f"p-{has_plist}"
            if has_plist:
                plist.write_text("x")
            res = summarize_loops_dir(tmp_path / "missing", plist, launchctl_print_rc=plist_rc)
            assert set(res.keys()) == {"installed", "last_pass_ts", "last_pass_step", "build_log_passes"}
