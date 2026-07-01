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


# ─── PROP-I3: dispatcher must NOT call legacy is_dormant / write_dormant_sentinel ─
def test_dispatcher_does_not_call_legacy_dormant_symbols():
    """REQ-I3 grep with \\b word-boundary regex (upgraded per FIND-005)."""
    txt = DISPATCH_PY.read_text()
    for sym in ("is_dormant", "write_dormant_sentinel"):
        # Allow the WORD 'dormant' in comments; ban the SYMBOLS as call sites.
        # A call site takes the form <symbol>( or import <symbol>.
        call_re = re.compile(rf"\b{sym}\s*\(")
        import_re = re.compile(rf"\bimport\b[^\n]*\b{sym}\b|\bfrom\b[^\n]*\bimport\b[^\n]*\b{sym}\b")
        assert not call_re.search(txt), f"REQ-I3 violation: {sym} call site in dispatcher"
        assert not import_re.search(txt), f"REQ-I3 violation: {sym} imported in dispatcher"


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
