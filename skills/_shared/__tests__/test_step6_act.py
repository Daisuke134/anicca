"""PROP-T1..T5, PROP-E1, PROP-E3, PROP-E8 unit tests for lib.step6_act.

PURE helpers + enqueue I/O. Phase 2a RED for proactive-step6-act.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from lib.step6_act import (
    sanitize_name,
    task_filename,
    task_descriptor,
    enqueue_task_descriptor,
)


# ─── PROP-T3: sanitizer ────────────────────────────────────────────
class TestSanitizeName:
    @pytest.mark.parametrize("inp,expected", [
        ("scan-coconala", "scan-coconala"),
        ("Follow_Up", "follow_up"),  # lowercase + keep underscore
        ("scan coconala new", "scan-coconala-new"),  # space → dash
        ("a--b---c", "a-b-c"),  # collapse runs of dash
        ("UPPER123", "upper123"),
        ("日本語", "unnamed"),  # all non-ASCII → unnamed (FIND-005 fix)
        ("***", "unnamed"),  # symbol-only → unnamed
        ("", "unnamed"),
        # FIND-004 iter-1 fix (non-tautological): assert exact expected output.
        # スキャン → drops, "-coconala" remains, leading dash stripped per
        # REQ-T3 (iii) "collapse runs of `-` into one" + (iv) strip.
        ("スキャン-coconala", "coconala"),
        ("foo!@#bar", "foo-bar"),  # punctuation → single dash separator
        ("ABC-日本-XYZ", "abc-xyz"),  # mid-string drop + collapse
    ])
    def test_sanitize(self, inp, expected):
        assert sanitize_name(inp) == expected


# ─── PROP-T1 + T2: filename and descriptor shape ───────────────────
def test_task_filename_includes_ts_and_pass_id():
    fn = task_filename(ts=1782900000, pass_id="p-1782900000", name="scan-coconala-new")
    assert fn == "1782900000-p-1782900000-scan-coconala-new.json"


def test_task_descriptor_shape():
    d = task_descriptor(
        pass_id="p-1", ts=42,
        picked={"name": "x", "category": "scan-requests", "platform": "coconala"},
        budget="MEDIUM", slot="gig",
    )
    assert d == {
        "schema_version": 1,
        "pass_id": "p-1",
        "ts": 42,
        "picked": {"name": "x", "category": "scan-requests", "platform": "coconala"},
        "budget": "MEDIUM",
        "proactive_loop_origin": "step6-act",
        "slot": "gig",
    }


# ─── PROP-T1: enqueue creates file ─────────────────────────────────
def test_enqueue_creates_file(tmp_path):
    slot_dir = tmp_path / "loops" / "gig"
    descriptor = task_descriptor(
        pass_id="p-100", ts=100,
        picked={"name": "follow-up", "category": "follow-up", "platform": "coconala"},
        budget="MEDIUM", slot="gig",
    )
    result = enqueue_task_descriptor(slot_dir, descriptor)
    assert result["ok"] is True
    assert "filename" in result
    written_path = slot_dir / "tasks" / result["filename"]
    assert written_path.exists()
    parsed = json.loads(written_path.read_text())
    assert parsed == descriptor


# ─── PROP-E1: tasks/ dir autocreate ────────────────────────────────
def test_enqueue_autocreates_tasks_dir(tmp_path):
    slot_dir = tmp_path / "no-such-loops" / "gig"
    assert not slot_dir.exists()
    d = task_descriptor(pass_id="p-2", ts=2, picked={"name": "x"}, budget="LIGHT", slot="gig")
    enqueue_task_descriptor(slot_dir, d)
    assert (slot_dir / "tasks").exists()


# ─── PROP-T4 + EDGE-E3: idempotent on same pass_id ────────────────
def test_enqueue_skips_when_pass_id_already_present(tmp_path):
    slot_dir = tmp_path / "loops" / "gig"
    d1 = task_descriptor(pass_id="p-DUP", ts=1, picked={"name": "x"}, budget="LIGHT", slot="gig")
    r1 = enqueue_task_descriptor(slot_dir, d1)
    assert r1["ok"] is True
    # 2nd call with SAME pass_id but different ts/name → skipped
    d2 = task_descriptor(pass_id="p-DUP", ts=2, picked={"name": "y"}, budget="LIGHT", slot="gig")
    r2 = enqueue_task_descriptor(slot_dir, d2)
    assert r2["ok"] is False
    assert r2["status"] == "enqueue-skipped-dup"
    # Verify only ONE file exists
    files = list((slot_dir / "tasks").glob("*.json"))
    assert len(files) == 1


# ─── PROP-E8: write failure is caught, no crash ────────────────────
def test_enqueue_write_failure_returns_error(tmp_path):
    # Make tasks/ unwritable to force IOError
    slot_dir = tmp_path / "loops" / "gig"
    (slot_dir / "tasks").mkdir(parents=True)
    (slot_dir / "tasks").chmod(0o500)  # read+exec only
    d = task_descriptor(pass_id="p-FAIL", ts=1, picked={"name": "x"}, budget="LIGHT", slot="gig")
    try:
        r = enqueue_task_descriptor(slot_dir, d)
        assert r["ok"] is False
        assert "status" in r
    finally:
        (slot_dir / "tasks").chmod(0o755)  # restore for cleanup


# ─── PROP-T5: outcome string format ────────────────────────────────
def test_enqueue_result_filename_for_build_log_outcome(tmp_path):
    slot_dir = tmp_path / "loops" / "gig"
    d = task_descriptor(pass_id="p-OUT", ts=1, picked={"name": "scan-new"}, budget="MEDIUM", slot="gig")
    r = enqueue_task_descriptor(slot_dir, d)
    # The dispatcher will build outcome = f"enqueued:{r['filename']}"; verify the
    # filename string is suitable (no whitespace, no slashes).
    assert " " not in r["filename"]
    assert "/" not in r["filename"]
    assert r["filename"].endswith(".json")
