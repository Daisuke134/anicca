"""PROP-M2: dispatcher STEP 6 reconciler branch integration + INV-4 SHA proof."""
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


def _run_dispatch(slot: str, slot_dir: Path, env_extra: dict | None = None):
    env = {**os.environ,
           "ANICCA_SLOT": slot,
           "ANICCA_SHARED_DIR": str(SHARED_DIR),
           "ANICCA_LOCK_PATH": str(slot_dir / ".proactive.lock"),
           "ANICCA_HAS_SESSION": "true",
           "ANICCA_LAST_PASS_MTIME": str(int(time.time())),
           "ANICCA_LAST_START_MTIME": str(int(time.time())),
           }
    if env_extra:
        env.update(env_extra)
    slot_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.run(["python3", str(DISPATCH_PY)],
                          capture_output=True, text=True, timeout=15, env=env)


def test_reconciler_pick_does_NOT_enqueue_task_and_runs_in_process(tmp_path, monkeypatch):
    """PROP-M2: reconciler category pick → reconcile in-process,
    tasks/*.json count UNCHANGED, build_log outcome starts with reconciled:."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "recprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "state").mkdir()
    # Menu has ONLY the reconciler item
    (slot_dir / "menu.json").write_text(json.dumps({
        "schema_version": 1,
        "categories": [{
            "name": "reconcile-earnings",
            "category": "reconciler",
            "platform": "internal",
            "roi_estimate_jpy": 0,
            "probability_of_landing": 1.0,
            "expected_settlement_days": 0,
            "required_budget": "LIGHT",
            "blocker_check": None,
            "min_cadence_seconds": 0,
        }],
        "novelty_quota_ratio": 0.0,
    }))
    # Seed one settle event that WILL match an existing roi row
    (slot_dir / "roi.jsonl").write_text(json.dumps({
        "schema_version": 1, "ts": 100, "pass_id": "p-42",
        "slot": slot, "budget": "MEDIUM", "picked": "x",
        "outcome": "enqueued:x", "roi_jpy_realized": 0, "roi_jpy_expected": 5000,
    }) + "\n")
    (slot_dir / "settle.jsonl").write_text(json.dumps({
        "schema_version": 1, "ts": 200, "pass_id": "p-42",
        "slot": slot, "jpy": 3000, "source": "coconala", "evidence": "kenshu-42",
    }) + "\n")

    tasks_before = set((slot_dir / "tasks").glob("*.json")) if (slot_dir / "tasks").exists() else set()

    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0, f"dispatch failed: {r.stderr}"

    # (b) tasks/*.json file count UNCHANGED
    tasks_after = set((slot_dir / "tasks").glob("*.json")) if (slot_dir / "tasks").exists() else set()
    assert tasks_after == tasks_before, f"REQ-M2 violation: tasks/ changed: {tasks_after - tasks_before}"

    # (d) build_log outcome starts with "reconciled:matched="
    body = (slot_dir / "build_log.md").read_text()
    assert "reconciled:matched=" in body, f"build_log outcome missing: {body[:500]}"

    # (e) state/reconciler-last-run.json exists and shows matched > 0
    marker = json.loads((slot_dir / "state" / "reconciler-last-run.json").read_text())
    assert marker["matched"] == 1
    assert marker["updated_rows"] == 1

    # (a) reconcile invoked in-process: the roi row is updated
    rows = [json.loads(l) for l in (slot_dir / "roi.jsonl").read_text().splitlines()]
    p42 = [r for r in rows if r["pass_id"] == "p-42"][0]
    assert p42["roi_jpy_realized"] == 3000


def test_step6_act_source_does_not_reference_reconciler_report_field():
    """PROP-M2(c): FIND-2-001 — the frozen task_descriptor shape must NOT
    gain a 'reconciler_report' field. Grep guards this."""
    src = (SHARED_DIR / "lib" / "step6_act.py").read_text()
    assert "reconciler_report" not in src, \
        "PROP-M2 regression: task_descriptor gained reconciler_report field"


# ─── INV-4: dispatcher run + reconciler NEVER writes ~/gig/ (SHA proof) ───
def test_reconciler_never_touches_gig_ledger(tmp_path, monkeypatch):
    """FIND-2-002 fix: SHA-256 + os.stat size + recursive hash + source grep.
    NO mtime predicate anywhere."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "gigprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "state").mkdir()
    (slot_dir / "menu.json").write_text(json.dumps({
        "schema_version": 1,
        "categories": [{
            "name": "reconcile-earnings", "category": "reconciler",
            "platform": "internal", "roi_estimate_jpy": 0,
            "probability_of_landing": 1.0, "expected_settlement_days": 0,
            "required_budget": "LIGHT", "min_cadence_seconds": 0,
        }],
        "novelty_quota_ratio": 0.0,
    }))
    (slot_dir / "roi.jsonl").write_text(json.dumps({
        "schema_version": 1, "ts": 100, "pass_id": "p-1", "slot": slot,
        "budget": "M", "picked": "x", "outcome": "e", "roi_jpy_realized": 0,
        "roi_jpy_expected": 0,
    }) + "\n")

    # Fake ~/gig with a canary ledger
    fake_gig = tmp_path / "gig"
    fake_gig.mkdir()
    (fake_gig / "earnings.jsonl").write_text('{"ledger": "canary", "value": 42}\n')
    (fake_gig / "applied.jsonl").write_text('{"ledger": "applied-canary"}\n')

    def sha_dir(d: Path) -> dict:
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() + f":{p.stat().st_size}"
                for p in sorted(d.glob("*.jsonl"))}

    before = sha_dir(fake_gig)
    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0
    after = sha_dir(fake_gig)
    assert before == after, f"INV-4 violation: ~/gig changed: {before} → {after}"


def test_reconciler_source_never_references_earnings_jsonl():
    """REQ-I2 static grep: reconciler.py must NOT mention earnings.jsonl at all."""
    src = (SHARED_DIR / "lib" / "reconciler.py").read_text()
    assert "earnings.jsonl" not in src
    # gig-path write patterns
    for pat in [r"open\([^)]*gig[^)]*['\"]w", r"open\([^)]*gig[^)]*['\"]a"]:
        m = re.search(pat, src)
        assert not m, f"REQ-I2 violation: write-mode reference to gig-path: {pat}"
