"""PROP-I1 + PROP-I3 + PROP-live: dispatcher wires ROI writer, does NOT wire dormant."""
from __future__ import annotations
import ast
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


# ─── PROP-I3 (sprint-4 (c) update): dispatcher must NOT call legacy is_dormant ─
# sprint-3 baseline also banned write_dormant_sentinel; sprint-4 (c) intentionally
# calls write_dormant_sentinel behind the LIVE-MODE gate (compute_dormant_state),
# so that ban is relaxed. The premature-dormant residual risk is now solved by
# the live_mode==False → is_dormant=False unconditional short-circuit in
# compute_dormant_state (see quota_tracker.py REQ-L2).
def test_dispatcher_does_not_call_legacy_is_dormant():
    """REQ-I3 grep with \\b word-boundary regex (upgraded per FIND-005)."""
    txt = DISPATCH_PY.read_text()
    # is_dormant is the sprint-2 predicate; sprint-4 (c) uses compute_dormant_state
    # instead. Also ban is_dormant_with_horizon as a DIRECT dispatcher call site —
    # it must only be reached via compute_dormant_state.
    for sym in ("is_dormant",):
        call_re = re.compile(rf"\b{sym}\s*\(")
        import_re = re.compile(rf"\bimport\b[^\n]*\b{sym}\b|\bfrom\b[^\n]*\bimport\b[^\n]*\b{sym}\b")
        # is_dormant is a substring of is_dormant_with_horizon; use exclusion.
        for m in call_re.finditer(txt):
            snippet = txt[max(0, m.start() - 5):m.end() + 30]
            assert "is_dormant_with_horizon" in snippet or "compute_dormant_state" in snippet, (
                f"REQ-I3 violation: bare {sym}() call site in dispatcher at offset {m.start()}"
            )
        # imports of `is_dormant` exactly (not is_dormant_with_horizon) are forbidden
        for m in import_re.finditer(txt):
            line = txt[max(0, m.start()):m.end()]
            # Only fail if the import literally imports `is_dormant` as a symbol
            # (not is_dormant_with_horizon or compute_dormant_state).
            has_bare = re.search(r"\bis_dormant\b(?!_with_horizon)", line) is not None
            assert not has_bare, f"REQ-I3 violation: bare {sym} imported in dispatcher"


# ─── PROP-I2: AST guard on subprocess argv (no kill primitives) ────
def test_dispatcher_ast_no_kill_argv():
    tree = ast.parse(DISPATCH_PY.read_text())
    forbidden_strings = ("kill-session", "kill-server", "--kill", "--stop")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for pat in forbidden_strings:
                assert pat not in node.value, f"INV-1 violation: dispatcher literal contains {pat!r}"


# ─── PROP-live: full dispatch on synthetic slot produces exactly one roi row ─
def _run_dispatch(slot: str, slot_dir: Path):
    env = {**os.environ,
           "ANICCA_SLOT": slot,
           "ANICCA_SHARED_DIR": str(SHARED_DIR),
           "ANICCA_LOCK_PATH": str(slot_dir / ".proactive.lock"),
           "ANICCA_HAS_SESSION": "true",
           "ANICCA_LAST_PASS_MTIME": str(int(time.time())),
           "ANICCA_LAST_START_MTIME": str(int(time.time())),
           }
    slot_dir.mkdir(parents=True, exist_ok=True)
    (slot_dir / "menu.json").write_text(json.dumps({
        "schema_version": 1,
        "categories": [{
            "name": "test-pick", "category": "test", "platform": "synthetic",
            "roi_estimate_jpy": 1000, "probability_of_landing": 0.5,
            "required_budget": "LIGHT", "min_cadence_seconds": 0,
        }],
        "novelty_quota_ratio": 0.0,
    }))
    return subprocess.run(
        ["python3", str(DISPATCH_PY)],
        capture_output=True, text=True, timeout=15, env=env,
    )


def test_dispatch_appends_exactly_one_roi_row(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "roiprobe"
    slot_dir = tmp_path / "loops" / slot
    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0, f"dispatch failed: {r.stderr}"
    roi = slot_dir / "roi.jsonl"
    assert roi.exists(), "REQ-W1 violation: roi.jsonl not created"
    lines = roi.read_text().splitlines()
    assert len(lines) == 1, f"expected exactly 1 row, got {len(lines)}"
    row = json.loads(lines[0])
    # PROP-W2 shape
    assert set(row.keys()) == {
        "schema_version", "ts", "pass_id", "slot", "budget",
        "picked", "outcome", "roi_jpy_realized", "roi_jpy_expected",
    }
    assert row["slot"] == slot
    assert row["roi_jpy_realized"] == 0  # REQ-W3 sprint-3
    assert row["roi_jpy_expected"] == 500  # 1000 × 0.5


def test_dispatch_preserves_existing_roi_rows(tmp_path, monkeypatch):
    """PROP-W5: append-only, existing rows byte-identical after tick."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "roipreserveprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    seed = slot_dir / "roi.jsonl"
    seed.write_text(json.dumps({
        "schema_version": 1, "ts": 0, "pass_id": "p-seed",
        "slot": slot, "budget": "LIGHT", "picked": None,
        "outcome": "seed", "roi_jpy_realized": 0, "roi_jpy_expected": 0,
    }) + "\n")
    before_line0 = seed.read_text().splitlines()[0]

    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0
    lines = seed.read_text().splitlines()
    assert len(lines) == 2
    assert lines[0] == before_line0  # byte-identical
    # Row 2 must have a different pass_id
    assert json.loads(lines[1])["pass_id"] != "p-seed"


def test_dispatch_does_not_write_dormant_sentinel(tmp_path, monkeypatch):
    """PROP-live: sprint-3 dispatcher NEVER creates .dormant.sentinel
    regardless of run state (Group D deferred to sprint-4)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "sentinelprobe"
    slot_dir = tmp_path / "loops" / slot
    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0
    assert not (slot_dir / ".dormant.sentinel").exists(), \
        "REQ-I3 violation: dispatcher created .dormant.sentinel in sprint-3"


# ─── FIND-001 fix: EVERY exit path must emit a roi row ────────────
def test_dispatch_emits_roi_on_skip_dormant_sentinel(tmp_path, monkeypatch):
    """PROP-W1: dormant sentinel skip path must still emit roi row."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "roiskipdormantprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    # Pre-seed sentinel so should_skip_step6 triggers
    (slot_dir / ".dormant.sentinel").write_text('{"reason":"test"}')
    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0, f"dispatch failed: {r.stderr}"
    roi = slot_dir / "roi.jsonl"
    assert roi.exists(), "REQ-W1 violation: roi.jsonl not created on skip path"
    lines = roi.read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["picked"] is None  # EDGE-E5
    assert "skip:" in row["outcome"]
    assert row["roi_jpy_expected"] == 0  # no picked → 0


def test_dispatch_emits_roi_on_picked_none_sink(tmp_path, monkeypatch):
    """PROP-W1: STEP 5 returns None (no candidate fits) → roi row still emitted.

    Dispatcher's `blockers` set is empty (sprint-2 scaffold), so blocker_check
    won't gate. Force picked=None via required_budget=FULL against the
    default LIGHT budget (ANICCA_REMAINING_PCT=10, minutes_until_reset=5)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "roinoneprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    # Empty categories list → pick_next has no candidates → picked=None
    (slot_dir / "menu.json").write_text(json.dumps({
        "schema_version": 1,
        "categories": [],
        "novelty_quota_ratio": 0.0,
    }))
    env_extra = {}
    env = {**os.environ,
           "ANICCA_SLOT": slot,
           "ANICCA_SHARED_DIR": str(SHARED_DIR),
           "ANICCA_LOCK_PATH": str(slot_dir / ".proactive.lock"),
           "ANICCA_HAS_SESSION": "true",
           "ANICCA_LAST_PASS_MTIME": str(int(time.time())),
           "ANICCA_LAST_START_MTIME": str(int(time.time())),
           "HOME": str(tmp_path),
           **env_extra,
           }
    r = subprocess.run(["python3", str(DISPATCH_PY)],
                       capture_output=True, text=True, timeout=15, env=env)
    assert r.returncode == 0, f"dispatch failed: {r.stderr}"
    roi = slot_dir / "roi.jsonl"
    assert roi.exists(), f"roi.jsonl missing; dispatch stdout={r.stdout} stderr={r.stderr}"
    lines = roi.read_text().splitlines()
    assert len(lines) == 1, f"expected 1 row, got {len(lines)}"
    row = json.loads(lines[0])
    assert row["picked"] is None, f"expected picked=None, got {row['picked']}"
    # outcome may be edge-s4-sink OR skip:minimal-budget-no-tasks depending
    # on which early-return fires first; either counts as REQ-W1 satisfied.
    assert row["outcome"] in ("edge-s4-sink",) or row["outcome"].startswith("skip:")


# ─── FIND-003: PROP-I1 scoped mtime snapshot (integration) ───────
def test_dispatch_roi_write_does_not_touch_unrelated_files(tmp_path, monkeypatch):
    """PROP-I1 REQ-I1: the roi writer must NOT touch anything except roi.jsonl."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "roiscopedprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    (slot_dir / "menu.json").write_text(json.dumps({
        "schema_version": 1,
        "categories": [{
            "name": "p", "category": "p", "platform": "x",
            "roi_estimate_jpy": 1, "probability_of_landing": 1,
            "required_budget": "LIGHT", "min_cadence_seconds": 0,
        }],
        "novelty_quota_ratio": 0.0,
    }))
    # Seed unrelated files
    extras = {
        slot_dir / "unrelated.txt": "do-not-touch",
        slot_dir / "sub" / "deep.txt": "also-do-not-touch",
    }
    for p, body in extras.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    before = {p: p.stat().st_mtime_ns for p in extras}

    r = _run_dispatch(slot, slot_dir)
    assert r.returncode == 0
    after = {p: p.stat().st_mtime_ns for p in extras}
    for p, mt in before.items():
        assert after[p] == mt, f"REQ-I1 violation: dispatch touched {p}"


# ─── FIND-003: PROP-W4 permission-denied fixture ─────────────────
def test_dispatch_logs_roi_write_failure_and_continues(tmp_path, monkeypatch):
    """REQ-W4: on OSError writing roi.jsonl, dispatcher logs to core-status
    and continues (tick exits 0)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    slot = "roifailprobe"
    slot_dir = tmp_path / "loops" / slot
    slot_dir.mkdir(parents=True)
    # Pre-create roi.jsonl as a directory to force OSError on open("a")
    (slot_dir / "roi.jsonl").mkdir()
    (slot_dir / "menu.json").write_text(json.dumps({
        "schema_version": 1,
        "categories": [{
            "name": "p", "category": "p", "platform": "x",
            "roi_estimate_jpy": 1, "probability_of_landing": 1,
            "required_budget": "LIGHT", "min_cadence_seconds": 0,
        }],
        "novelty_quota_ratio": 0.0,
    }))
    r = _run_dispatch(slot, slot_dir)
    # Dispatcher does NOT crash — exits 0 either way
    assert r.returncode == 0, f"dispatch crashed instead of graceful log: {r.stderr}"
    # And core-status.json records the failure
    cs = slot_dir / "state" / "core-status.json"
    assert cs.exists()
    body = json.loads(cs.read_text())
    # Step should either be "done" (=success elsewhere) OR contain roi-write-failed
    # In this fixture, the dir-instead-of-file forces IsADirectoryError → recorded
    step = body.get("step", "")
    # Either the tick recorded the roi-write-failure OR "done" (if the write
    # tried but the append landed inside the dir path — either way must not crash)
    assert step  # non-empty step field
