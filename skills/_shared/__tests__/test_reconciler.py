"""PROP-R1..R8, PROP-E1..E9, PROP-I1..I5 for lib.reconciler."""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
import pytest

from lib.reconciler import (
    parse_settle_line,
    merge_realized,
    reconcile,
)


# ─── PROP-R1: pure parse ───────────────────────────────────────────
class TestParseSettleLine:
    def test_valid_line(self):
        row = parse_settle_line('{"schema_version":1,"ts":1,"pass_id":"p-1","slot":"gig","jpy":3000,"source":"coconala","evidence":"kenshu-42"}')
        assert row["pass_id"] == "p-1"
        assert row["jpy"] == 3000

    def test_malformed_json(self):
        assert parse_settle_line("{ not valid") is None

    def test_empty(self):
        assert parse_settle_line("") is None


# ─── PROP-R4 monotone MAX ─────────────────────────────────────────
class TestMergeRealized:
    def test_first_time_settle(self):
        v, s = merge_realized(0, 3000)
        assert v == 3000 and s == "updated"

    def test_partial_then_full_upgrades(self):
        v, s = merge_realized(1000, 3000)
        assert v == 3000 and s == "updated"

    def test_same_value_noop(self):
        v, s = merge_realized(3000, 3000)
        assert v == 3000 and s == "noop"

    def test_lower_new_skipped(self):
        v, s = merge_realized(3000, 1000)
        assert v == 3000 and s == "skipped_dup"

    def test_zero_new_skipped_when_existing_positive(self):
        v, s = merge_realized(3000, 0)
        assert v == 3000 and s == "skipped_dup"


def _write_roi_file(slot_dir: Path, rows: list[dict]) -> None:
    (slot_dir / "roi.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )


def _write_settle_file(slot_dir: Path, rows: list[dict]) -> None:
    (slot_dir / "settle.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )


def _roi_row(pass_id: str, realized: int = 0) -> dict:
    return {"schema_version": 1, "ts": 100, "pass_id": pass_id,
            "slot": "gig", "budget": "MEDIUM", "picked": "x",
            "outcome": "enqueued:x", "roi_jpy_realized": realized,
            "roi_jpy_expected": 5000}


def _settle_row(pass_id: str, jpy: int, ts: int = 200) -> dict:
    return {"schema_version": 1, "ts": ts, "pass_id": pass_id,
            "slot": "gig", "jpy": jpy, "source": "coconala",
            "evidence": f"kenshu-{pass_id}"}


# ─── PROP-R1: match updates roi ────────────────────────────────────
def test_reconcile_match_updates_roi(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0), _roi_row("p-2", 0)])
    _write_settle_file(slot, [_settle_row("p-1", 3000)])
    report = reconcile(slot, now_ts=1000)
    assert report["matched"] == 1
    assert report["updated_rows"] == 1
    rows = [json.loads(l) for l in (slot / "roi.jsonl").read_text().splitlines()]
    p1 = [r for r in rows if r["pass_id"] == "p-1"][0]
    p2 = [r for r in rows if r["pass_id"] == "p-2"][0]
    assert p1["roi_jpy_realized"] == 3000
    assert p2["roi_jpy_realized"] == 0


# ─── PROP-R1: unknown pass_id → unmatched ────────────────────────
def test_reconcile_unknown_pass_id_goes_to_unmatched(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    _write_settle_file(slot, [_settle_row("p-99", 4000)])
    report = reconcile(slot, now_ts=1000)
    assert report["matched"] == 0
    assert report["unmatched"] == 1
    unmatched = (slot / ".unmatched.jsonl").read_text().splitlines()
    assert len(unmatched) == 1
    body = json.loads(unmatched[0])
    assert body["pass_id"] == "p-99"
    assert body["reason"] == "unknown-pass-id"


# ─── PROP-R4 monotone via integration ────────────────────────────
def test_reconcile_never_decreases_realized(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 3000)])
    _write_settle_file(slot, [_settle_row("p-1", 1000)])
    report = reconcile(slot, now_ts=1000)
    assert report["skipped_dup"] == 1
    rows = [json.loads(l) for l in (slot / "roi.jsonl").read_text().splitlines()]
    assert rows[0]["roi_jpy_realized"] == 3000  # unchanged


def test_reconcile_upgrades_partial_to_full(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 1000)])
    _write_settle_file(slot, [_settle_row("p-1", 3000)])
    report = reconcile(slot, now_ts=1000)
    assert report["updated_rows"] == 1
    rows = [json.loads(l) for l in (slot / "roi.jsonl").read_text().splitlines()]
    assert rows[0]["roi_jpy_realized"] == 3000


# ─── PROP-R6: marker written ──────────────────────────────────────
def test_reconcile_writes_last_run_marker(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    _write_settle_file(slot, [_settle_row("p-1", 5000)])
    reconcile(slot, now_ts=1000)
    marker = json.loads((slot / "state" / "reconciler-last-run.json").read_text())
    assert marker["matched"] == 1
    assert marker["updated_rows"] == 1


# ─── PROP-R8: offset advances + prevents replay ──────────────────
def test_reconcile_offset_prevents_second_run_reprocess(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    _write_settle_file(slot, [_settle_row("p-1", 3000)])
    r1 = reconcile(slot, now_ts=1000)
    assert r1["matched"] == 1
    r2 = reconcile(slot, now_ts=2000)
    assert r2["matched"] == 0  # offset skipped the already-processed row


def test_reconcile_offset_reset_when_offset_ahead_of_file(tmp_path):
    """EDGE-E9: offset > file length (file rotated + truncated to fewer lines).
    Reset offset to 0 so we reprocess the shrunk file."""
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    _write_settle_file(slot, [
        _settle_row("p-1", 3000),
        _settle_row("p-2", 1000),  # will be unmatched-then-processed
        _settle_row("p-3", 500),
    ])
    reconcile(slot, now_ts=1000)  # offset advances to 3
    # Simulate rotation: replace with a 1-line file (fewer lines than offset)
    _write_settle_file(slot, [_settle_row("p-1", 5000)])
    r = reconcile(slot, now_ts=2000)
    # offset (3) > file len (1) → E9 reset to 0 → process the 1 line → p-1
    # merges 3000 → 5000 (monotone-max upgrade)
    assert r["matched"] == 1 and r["updated_rows"] == 1
    rows = [json.loads(l) for l in (slot / "roi.jsonl").read_text().splitlines()]
    assert rows[0]["roi_jpy_realized"] == 5000


# ─── PROP-E1: missing settle file ────────────────────────────────
def test_reconcile_no_settle_file(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    report = reconcile(slot, now_ts=1000)
    assert report["matched"] == 0
    assert report["unmatched"] == 0


# ─── PROP-E2: missing roi file ───────────────────────────────────
def test_reconcile_no_roi_file(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_settle_file(slot, [_settle_row("p-1", 3000)])
    report = reconcile(slot, now_ts=1000)
    assert report["matched"] == 0
    assert report["unmatched"] == 1  # no roi to match → goes to unmatched


# ─── PROP-E3: malformed settle line ──────────────────────────────
def test_reconcile_malformed_settle_line_goes_to_unmatched(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    (slot / "settle.jsonl").write_text('{ not valid\n' + json.dumps(_settle_row("p-1", 3000)) + "\n")
    report = reconcile(slot, now_ts=1000)
    assert report["matched"] == 1
    unmatched = (slot / ".unmatched.jsonl").read_text().splitlines()
    assert len(unmatched) == 1
    body = json.loads(unmatched[0])
    assert body["reason"] == "malformed-json"


# ─── PROP-E5 dup ──────────────────────────────────────────────────
def test_reconcile_duplicate_settle_rows_highest_wins(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    _write_settle_file(slot, [
        _settle_row("p-1", 1000, ts=100),
        _settle_row("p-1", 3000, ts=200),
        _settle_row("p-1", 2000, ts=300),
    ])
    reconcile(slot, now_ts=1000)
    rows = [json.loads(l) for l in (slot / "roi.jsonl").read_text().splitlines()]
    assert rows[0]["roi_jpy_realized"] == 3000  # HIGHEST wins


# ─── PROP-R7a: unmatched dedup by (pass_id, ts) ─────────────────
def test_reconcile_dedup_unmatched_by_pass_id_ts(tmp_path):
    slot = tmp_path / "gig"
    slot.mkdir()
    (slot / "state").mkdir()
    _write_roi_file(slot, [_roi_row("p-1", 0)])
    # Pre-seed .unmatched with the same (pass_id, ts) pair
    (slot / ".unmatched.jsonl").write_text(
        json.dumps({**_settle_row("p-999", 500, ts=42), "reason": "unknown-pass-id"}) + "\n"
    )
    # Now try to add the same one again
    _write_settle_file(slot, [_settle_row("p-999", 500, ts=42)])
    reconcile(slot, now_ts=1000)
    unmatched = (slot / ".unmatched.jsonl").read_text().splitlines()
    # Should still be just 1 line (dedup worked)
    assert len(unmatched) == 1


# ─── PROP-I1: no tmux kill ───────────────────────────────────────
def test_reconciler_source_has_no_tmux_kill():
    src = (Path(__file__).resolve().parents[1] / "lib" / "reconciler.py").read_text()
    forbidden = [r"tmux\s+kill", r"--stop\b", r"--kill\b", r"kill-session", r"kill-server"]
    for pat in forbidden:
        m = re.search(pat, src)
        assert not m, f"INV-1 violation: reconciler.py contains {pat!r}"


# ─── PROP-I3: no human-touch ─────────────────────────────────────
def test_reconciler_source_no_human_touch():
    src = (Path(__file__).resolve().parents[1] / "lib" / "reconciler.py").read_text()
    forbidden = [r"\bosascript\b", r"terminal-notifier", r"telegram\.org",
                 r"hooks\.slack", r"\btwilio\b", r"\bSecKeychain\b",
                 r"find-generic-password"]
    for pat in forbidden:
        m = re.search(pat, src)
        assert not m, f"REQ-I3 violation: reconciler.py contains {pat!r}"


# ─── PROP-I4: no shell injection ─────────────────────────────────
def test_reconciler_source_no_shell_true_or_os_system():
    src = (Path(__file__).resolve().parents[1] / "lib" / "reconciler.py").read_text()
    forbidden_shell = "shell=True"
    assert forbidden_shell not in src
    forbidden_os = "os." + "system("
    assert forbidden_os not in src


# ─── PROP-I2: never writes ~/gig via source-grep ─────────────────
def test_reconciler_source_never_writes_gig():
    """REQ-I2 static check: no write-mode string reference to ~/gig or
    earnings.jsonl in the reconciler source."""
    src = (Path(__file__).resolve().parents[1] / "lib" / "reconciler.py").read_text()
    # Any mention of the string 'earnings.jsonl' at all (writes MUST be 0)
    assert "earnings.jsonl" not in src, \
        "REQ-I2: reconciler.py must NOT reference earnings.jsonl (READ handled elsewhere; this feature does NOT read earnings.jsonl either)"
    # Any mention of ~/gig with a write-mode file open call
    write_patterns = [r"open\([^)]*~/gig", r"write_text\([^)]*~/gig",
                      r'open\([^)]*"a"[^)]*gig', r'open\([^)]*"w"[^)]*gig']
    for pat in write_patterns:
        m = re.search(pat, src)
        assert not m, f"REQ-I2 violation: write-mode ~/gig reference: {pat!r}"
