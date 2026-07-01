"""PROP-R1..R6 + INV grep tests for lib.settle_mirror."""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
import pytest

from lib.settle_mirror import (
    parse_earnings_line,
    is_settled_row,
    extract_pass_id_or_sentinel,
    build_settle_row,
    settle_row_dedup_key,
    mirror_earnings_to_settle,
    SETTLED_STATUSES,
)


# ─── PROP-R1 pure parse ────────────────────────────────────────────
class TestParseEarnings:
    def test_valid(self):
        r = parse_earnings_line('{"ts":100,"requestId":"5123100","jpy":40000,"status":"検収","pass_id":"p-42"}')
        assert r["requestId"] == "5123100"
        assert r["pass_id"] == "p-42"

    def test_malformed(self):
        assert parse_earnings_line("{ nope") is None

    def test_empty(self):
        assert parse_earnings_line("") is None


# ─── PROP-E3 non-settled + zero-jpy compound ────────────────────
class TestIsSettled:
    def test_settled_positive_jpy(self):
        assert is_settled_row({"status": "検収", "jpy": 100}) is True
        assert is_settled_row({"status": "支払", "jpy": 500}) is True
        assert is_settled_row({"status": "paid", "jpy": 100}) is True
        assert is_settled_row({"status": "completed", "jpy": 100}) is True
        assert is_settled_row({"status": "検収完了", "jpy": 100}) is True

    def test_non_settled_status(self):
        assert is_settled_row({"status": "applied", "jpy": 100}) is False
        assert is_settled_row({"status": "in_progress", "jpy": 100}) is False

    def test_zero_or_missing_jpy(self):
        assert is_settled_row({"status": "検収", "jpy": 0}) is False
        assert is_settled_row({"status": "検収"}) is False

    def test_non_numeric_jpy(self):
        assert is_settled_row({"status": "検収", "jpy": "not-a-number"}) is False


# ─── PROP-R3i direct pass_id read + PROP-E4 fallback ─────────────
class TestExtractPassId:
    def test_direct_valid_pass_id(self):
        pid = extract_pass_id_or_sentinel({"pass_id": "p-1782887606", "requestId": "5123100"})
        assert pid == "p-1782887606"

    def test_missing_pass_id_returns_sentinel(self):
        pid = extract_pass_id_or_sentinel({"requestId": "5123100"})
        assert pid == "unmatched-requestId-5123100"

    def test_malformed_pass_id_returns_sentinel(self):
        # PROP-E4: pass_id present but doesn't match ^p-\d+$
        pid = extract_pass_id_or_sentinel({"pass_id": "not-a-real-id", "requestId": "5123100"})
        assert pid == "unmatched-requestId-5123100"

    def test_numeric_requestId_becomes_string_in_sentinel(self):
        pid = extract_pass_id_or_sentinel({"requestId": 5123100})
        assert pid == "unmatched-requestId-5123100"


# ─── PROP-R3iii build_settle_row shape ───────────────────────────
class TestBuildSettleRow:
    def test_top_level_fields(self):
        row = build_settle_row(
            pass_id="p-42", requestId="5123", jpy=3000,
            status="検収", ts=1000, slot="gig",
            earnings_ts="2026-07-01T15:00:00+09:00",
        )
        # Top-level requestId + earnings_status (REQ-R3iii FIND-004 fix)
        assert row["requestId"] == "5123"
        assert row["earnings_status"] == "検収"
        assert row["pass_id"] == "p-42"
        assert row["jpy"] == 3000
        assert row["source"] == "coconala-earnings-mirror"


# ─── PROP-R5 dedup key ────────────────────────────────────────────
def test_settle_row_dedup_key():
    row = build_settle_row(pass_id="p-1", requestId="5123", jpy=100, status="検収",
                            ts=1, slot="gig", earnings_ts="x")
    assert settle_row_dedup_key(row) == ("5123", "検収")


# ─── Integration: full mirror flow ─────────────────────────────────
def _write_earnings(slot_dir: Path, gig_dir: Path, rows: list[dict]):
    gig_dir.mkdir(parents=True, exist_ok=True)
    (gig_dir / "earnings.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )


def test_mirror_appends_settle_for_matched_pass_id(tmp_path):
    slot = tmp_path / "loops" / "gig"
    slot.mkdir(parents=True)
    (slot / "state").mkdir()
    gig = tmp_path / "gig"
    _write_earnings(slot, gig, [
        {"ts": 100, "requestId": "5123100", "jpy": 40000, "status": "検収",
         "pass_id": "p-1782887606"},
    ])
    r = mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=2000)
    assert r["new"] == 1
    assert r["unmatched"] == 0
    settle_lines = (slot / "settle.jsonl").read_text().splitlines()
    assert len(settle_lines) == 1
    row = json.loads(settle_lines[0])
    assert row["pass_id"] == "p-1782887606"
    assert row["requestId"] == "5123100"
    assert row["jpy"] == 40000


def test_mirror_uses_sentinel_for_missing_pass_id(tmp_path):
    slot = tmp_path / "loops" / "gig"
    slot.mkdir(parents=True)
    (slot / "state").mkdir()
    gig = tmp_path / "gig"
    _write_earnings(slot, gig, [
        {"ts": 100, "requestId": "5123100", "jpy": 40000, "status": "検収"},  # no pass_id
    ])
    r = mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=2000)
    assert r["new"] == 1
    assert r["unmatched"] == 1
    row = json.loads((slot / "settle.jsonl").read_text().splitlines()[0])
    assert row["pass_id"] == "unmatched-requestId-5123100"


def test_mirror_ignores_non_settled(tmp_path):
    slot = tmp_path / "loops" / "gig"
    slot.mkdir(parents=True)
    (slot / "state").mkdir()
    gig = tmp_path / "gig"
    _write_earnings(slot, gig, [
        {"ts": 100, "requestId": "1", "jpy": 100, "status": "applied"},
        {"ts": 200, "requestId": "2", "jpy": 100, "status": "in_progress"},
    ])
    r = mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=2000)
    assert r["new"] == 0


def test_mirror_dedup_by_requestId_and_status(tmp_path):
    slot = tmp_path / "loops" / "gig"
    slot.mkdir(parents=True)
    (slot / "state").mkdir()
    gig = tmp_path / "gig"
    # Seed a settle.jsonl with an existing row
    seed = build_settle_row(pass_id="p-1", requestId="5", jpy=100, status="検収",
                            ts=1, slot="gig", earnings_ts="x")
    (slot / "settle.jsonl").write_text(json.dumps(seed) + "\n")
    # Now the earnings has a matching (requestId, status) — should be dup
    _write_earnings(slot, gig, [
        {"ts": 200, "requestId": "5", "jpy": 999, "status": "検収", "pass_id": "p-9"},
    ])
    r = mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=2000)
    assert r["dup"] == 1
    assert r["new"] == 0


def test_mirror_offset_prevents_replay(tmp_path):
    slot = tmp_path / "loops" / "gig"
    slot.mkdir(parents=True)
    (slot / "state").mkdir()
    gig = tmp_path / "gig"
    _write_earnings(slot, gig, [
        {"ts": 100, "requestId": "5", "jpy": 100, "status": "検収", "pass_id": "p-1"},
    ])
    r1 = mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=1000)
    assert r1["new"] == 1
    r2 = mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=2000)
    assert r2["new"] == 0


# ─── INV-4 SHA proof ───────────────────────────────────────────────
def test_mirror_does_not_write_earnings(tmp_path):
    slot = tmp_path / "loops" / "gig"
    slot.mkdir(parents=True)
    (slot / "state").mkdir()
    gig = tmp_path / "gig"
    _write_earnings(slot, gig, [
        {"ts": 100, "requestId": "5", "jpy": 100, "status": "検収", "pass_id": "p-1"},
    ])
    before = hashlib.sha256((gig / "earnings.jsonl").read_bytes()).hexdigest()
    mirror_earnings_to_settle(slot, gig / "earnings.jsonl", now_ts=2000)
    after = hashlib.sha256((gig / "earnings.jsonl").read_bytes()).hexdigest()
    assert before == after


# ─── INV grep tests ────────────────────────────────────────────────
def test_source_no_shell_true():
    src = (Path(__file__).resolve().parents[1] / "lib" / "settle_mirror.py").read_text()
    assert "shell=True" not in src
    assert "os." + "system(" not in src


def test_source_no_human_touch():
    src = (Path(__file__).resolve().parents[1] / "lib" / "settle_mirror.py").read_text()
    for pat in [r"\bosascript\b", r"terminal-notifier", r"telegram\.org",
                r"hooks\.slack", r"\btwilio\b", r"\bSecKeychain\b",
                r"find-generic-password"]:
        assert not re.search(pat, src), f"human-touch surface {pat!r}"


def test_source_never_writes_earnings():
    src = (Path(__file__).resolve().parents[1] / "lib" / "settle_mirror.py").read_text()
    # No write-mode reference to earnings.jsonl or ~/gig
    for pat in [r"open\([^)]*earnings\.jsonl[^)]*['\"]w",
                r"open\([^)]*earnings\.jsonl[^)]*['\"]a",
                r"open\([^)]*~/gig[^)]*['\"]w",
                r"\.write.*earnings\.jsonl"]:
        assert not re.search(pat, src), f"REQ-I2 violation: {pat}"


def test_source_no_tmux_kill():
    src = (Path(__file__).resolve().parents[1] / "lib" / "settle_mirror.py").read_text()
    for pat in [r"tmux\s+kill", r"kill-session", r"kill-server", r"--stop", r"--kill"]:
        assert not re.search(pat, src), f"INV-1 violation: {pat}"

