"""PROP-M2 + PROP-integration-full-loop + PROP-integration-sentinel-path.

FIND-001 iter-1 fix: the spec promised this integration test file at
verification-architecture.md but it was missing. This provides the automated
coverage for the dispatcher STEP 6 elif branch + the full pipeline round-trip.
"""
from __future__ import annotations
import hashlib
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


def _menu_with(items: list[dict]) -> dict:
    return {"schema_version": 1, "categories": items, "novelty_quota_ratio": 0.0}


def _mirror_item() -> dict:
    return {
        "name": "settle-mirror",
        "category": "settle-mirror",
        "platform": "internal",
        "roi_estimate_jpy": 0,
        "probability_of_landing": 1.0,
        "expected_settlement_days": 0,
        "required_budget": "LIGHT",
        "blocker_check": None,
        "min_cadence_seconds": 0,
    }


def _reconciler_item() -> dict:
    return {
        "name": "reconcile-earnings",
        "category": "reconciler",
        "platform": "internal",
        "roi_estimate_jpy": 0,
        "probability_of_landing": 1.0,
        "expected_settlement_days": 0,
        "required_budget": "LIGHT",
        "blocker_check": None,
        "min_cadence_seconds": 0,
    }


def _run_dispatch(slot: str, slot_dir: Path, extra_env: dict | None = None):
    env = {
        **os.environ,
        "ANICCA_SLOT": slot,
        "ANICCA_SHARED_DIR": str(SHARED_DIR),
        "ANICCA_LOCK_PATH": str(slot_dir / ".proactive.lock"),
        "ANICCA_HAS_SESSION": "true",
        "ANICCA_LAST_PASS_MTIME": str(int(time.time())),
        "ANICCA_LAST_START_MTIME": str(int(time.time())),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["python3", str(DISPATCH_PY)],
        capture_output=True, text=True, timeout=15, env=env,
    )


def _seed_roi(slot_dir: Path, rows: list[dict]) -> None:
    (slot_dir / "roi.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )


def _roi_row(pass_id: str, realized: int = 0) -> dict:
    return {"schema_version": 1, "ts": 100, "pass_id": pass_id,
            "slot": "gig", "budget": "MEDIUM", "picked": "x",
            "outcome": "enqueued:x", "roi_jpy_realized": realized,
            "roi_jpy_expected": 5000}


# ─── PROP-M2: dispatcher invokes mirror in-process ────────────────
def test_dispatcher_invokes_mirror_in_process(tmp_path, monkeypatch):
    """PROP-M2: category=='settle-mirror' → in-process invoke + no tasks/
    descriptor + outcome starts with 'settle-mirror:new='."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "gig"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "state").mkdir()
    (slot_dir / "menu.json").write_text(json.dumps(_menu_with([_mirror_item()])))
    # Seed a settleable earnings row
    (tmp_path / "gig").mkdir()
    (tmp_path / "gig" / "earnings.jsonl").write_text(json.dumps({
        "ts": 100, "requestId": "5123100", "jpy": 40000,
        "status": "検収", "pass_id": "p-1782887606",
    }) + "\n")
    _seed_roi(slot_dir, [_roi_row("p-1782887606", 0)])

    tasks_before = set((slot_dir / "tasks").glob("*.json")) if (slot_dir / "tasks").exists() else set()

    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0, f"dispatch failed: {r.stderr}"

    # No tasks/ descriptor created for mirror pick
    tasks_after = set((slot_dir / "tasks").glob("*.json")) if (slot_dir / "tasks").exists() else set()
    assert tasks_after == tasks_before

    # build_log outcome starts with settle-mirror:new=
    body = (slot_dir / "build_log.md").read_text()
    assert "settle-mirror:new=" in body

    # settle.jsonl gained a row
    settle_lines = (slot_dir / "settle.jsonl").read_text().splitlines()
    assert len(settle_lines) == 1
    row = json.loads(settle_lines[0])
    assert row["pass_id"] == "p-1782887606"


# ─── PROP-integration-full-loop: earnings → mirror → settle → reconciler → roi ─
def test_full_pipeline_matched_pass_id_updates_roi(tmp_path, monkeypatch):
    """PROP-integration-full-loop: an earnings row with a matching pass_id
    propagates through the mirror + reconciler pipeline into roi_jpy_realized."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "gig"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "state").mkdir()
    (tmp_path / "gig").mkdir()

    # Menu has both mirror and reconciler (mirror runs first because
    # min_cadence_seconds=0, then reconciler runs on the next dispatch tick;
    # but here we chain 2 dispatch runs to model the sequence.)
    (slot_dir / "menu.json").write_text(json.dumps(_menu_with([_mirror_item()])))
    _seed_roi(slot_dir, [_roi_row("p-42", 0)])
    (tmp_path / "gig" / "earnings.jsonl").write_text(json.dumps({
        "ts": 100, "requestId": "9999", "jpy": 3000,
        "status": "検収", "pass_id": "p-42",
    }) + "\n")

    # Tick 1: mirror picks and runs
    r1 = _run_dispatch(slot, slot_dir)
    assert r1.returncode == 0, f"tick1: {r1.stderr}"

    # Settle.jsonl now has the row
    settle_lines = (slot_dir / "settle.jsonl").read_text().splitlines()
    assert len(settle_lines) == 1

    # Tick 2: switch menu to reconciler + rerun
    (slot_dir / "menu.json").write_text(json.dumps(_menu_with([_reconciler_item()])))
    r2 = _run_dispatch(slot, slot_dir)
    assert r2.returncode == 0, f"tick2: {r2.stderr}"

    # roi.jsonl row is updated
    rows = [json.loads(l) for l in (slot_dir / "roi.jsonl").read_text().splitlines()]
    p42 = [r for r in rows if r["pass_id"] == "p-42"][0]
    assert p42["roi_jpy_realized"] == 3000


# ─── PROP-integration-sentinel-path: no pass_id → .unmatched.jsonl ─
def test_full_pipeline_sentinel_path_creates_unmatched_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "gig"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "state").mkdir()
    (tmp_path / "gig").mkdir()

    (slot_dir / "menu.json").write_text(json.dumps(_menu_with([_mirror_item()])))
    _seed_roi(slot_dir, [_roi_row("p-100", 0)])
    # Earnings row WITHOUT pass_id
    (tmp_path / "gig" / "earnings.jsonl").write_text(json.dumps({
        "ts": 100, "requestId": "8888", "jpy": 4000, "status": "検収",
    }) + "\n")

    r1 = _run_dispatch(slot, slot_dir)
    assert r1.returncode == 0, f"tick1: {r1.stderr}"

    # settle.jsonl row has sentinel pass_id
    row = json.loads((slot_dir / "settle.jsonl").read_text().splitlines()[0])
    assert row["pass_id"] == "unmatched-requestId-8888"

    # Tick 2: reconciler routes it to .unmatched.jsonl
    (slot_dir / "menu.json").write_text(json.dumps(_menu_with([_reconciler_item()])))
    r2 = _run_dispatch(slot, slot_dir)
    assert r2.returncode == 0, f"tick2: {r2.stderr}"

    unmatched_lines = (slot_dir / ".unmatched.jsonl").read_text().splitlines()
    assert len(unmatched_lines) >= 1
    unmatched_row = json.loads(unmatched_lines[0])
    assert unmatched_row.get("reason") == "unknown-pass-id"
    assert unmatched_row.get("pass_id") == "unmatched-requestId-8888"


# ─── Guard against earnings_path derivation drift ─────────────────
def test_dispatcher_earnings_path_uses_gig_dir_for_gig_slot(tmp_path, monkeypatch):
    """FIND-001 secondary: dispatcher derives earnings_path from slot name.
    Confirm for slot='gig' it resolves to ~/gig/earnings.jsonl."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "gig"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "state").mkdir()
    (tmp_path / "gig").mkdir()
    # If dispatcher looked at the wrong path, no settle would be produced.
    (tmp_path / "gig" / "earnings.jsonl").write_text(json.dumps({
        "ts": 100, "requestId": "9", "jpy": 100, "status": "検収",
        "pass_id": "p-1",
    }) + "\n")
    (slot_dir / "menu.json").write_text(json.dumps(_menu_with([_mirror_item()])))
    _seed_roi(slot_dir, [_roi_row("p-1", 0)])

    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0
    assert (slot_dir / "settle.jsonl").exists(), \
        "dispatcher did not derive earnings_path correctly for slot='gig'"


# ─── Grep: dispatcher elif branch present and calls _mirror_slot ──
def test_dispatcher_source_has_settle_mirror_elif_branch():
    src = DISPATCH_PY.read_text()
    assert 'picked.get("category") == "settle-mirror"' in src, \
        "dispatcher missing settle-mirror elif branch"
    assert "_mirror_slot" in src, "dispatcher missing _mirror_slot invocation"
    assert 'f"settle-mirror:new=' in src, "dispatcher outcome format missing"
