"""PROP-W1..W5 + EDGE-E1/E5/E6/E7/E8 unit tests for lib.roi_track."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from lib.roi_track import roi_row, compute_expected_jpy, append_roi_row


# ─── PROP-W3 formula + edges ──────────────────────────────────────
class TestExpectedFormula:
    def test_basic_multiply(self):
        assert compute_expected_jpy({"roi_estimate_jpy": 40000, "probability_of_landing": 0.4}) == 16000

    def test_none_picked_returns_zero(self):
        assert compute_expected_jpy(None) == 0

    def test_missing_roi_field(self):
        assert compute_expected_jpy({"probability_of_landing": 0.5}) == 0

    def test_missing_prob_field(self):
        assert compute_expected_jpy({"roi_estimate_jpy": 1000}) == 0

    def test_prob_over_one_clamped(self):
        # EDGE-E7: prob > 1 clamped to 1
        assert compute_expected_jpy({"roi_estimate_jpy": 1000, "probability_of_landing": 1.5}) == 1000

    def test_prob_negative_clamped(self):
        assert compute_expected_jpy({"roi_estimate_jpy": 1000, "probability_of_landing": -0.2}) == 0

    def test_non_numeric_fields(self):
        assert compute_expected_jpy({"roi_estimate_jpy": "abc", "probability_of_landing": 0.5}) == 0


# ─── PROP-W2 shape ────────────────────────────────────────────────
class TestRowShape:
    def test_all_9_keys_present(self):
        r = roi_row(
            ts=1782900000, pass_id="p-1", slot="gig", budget="MEDIUM",
            picked="scan", outcome="enqueued:x.json",
        )
        assert set(r.keys()) == {
            "schema_version", "ts", "pass_id", "slot", "budget",
            "picked", "outcome", "roi_jpy_realized", "roi_jpy_expected",
        }

    def test_default_realized_and_expected_zero(self):
        r = roi_row(ts=1, pass_id="p", slot="gig", budget="LIGHT", picked=None, outcome="skip")
        assert r["roi_jpy_realized"] == 0
        assert r["roi_jpy_expected"] == 0

    def test_picked_none_is_json_serializable(self):
        r = roi_row(ts=1, pass_id="p", slot="gig", budget="LIGHT", picked=None, outcome="skip")
        # Must round-trip
        assert json.loads(json.dumps(r))["picked"] is None


# ─── PROP-W1 + W5 append ───────────────────────────────────────────
class TestAppendRoiRow:
    def test_first_write_creates_file(self, tmp_path):
        """EDGE-E1: creates file when missing."""
        p = tmp_path / "roi.jsonl"
        r = roi_row(ts=1, pass_id="p-1", slot="gig", budget="LIGHT", picked=None, outcome="ok")
        result = append_roi_row(p, r)
        assert result["ok"] is True
        assert p.exists()
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0]) == r

    def test_append_preserves_existing(self, tmp_path):
        """PROP-W5: never truncates; existing rows byte-identical."""
        p = tmp_path / "roi.jsonl"
        seed = {"schema_version": 1, "ts": 0, "pass_id": "p-0",
                "slot": "gig", "budget": "LIGHT", "picked": None,
                "outcome": "seed", "roi_jpy_realized": 0, "roi_jpy_expected": 0}
        p.write_text(json.dumps(seed) + "\n")
        before_bytes = p.read_bytes()

        r = roi_row(ts=1, pass_id="p-1", slot="gig", budget="LIGHT", picked=None, outcome="ok")
        append_roi_row(p, r)

        after = p.read_text().splitlines()
        assert len(after) == 2
        # Row 0 byte-identical
        assert after[0] == before_bytes.decode().strip()
        assert json.loads(after[1])["pass_id"] == "p-1"

    def test_write_failure_returns_error_dict(self, tmp_path):
        """PROP-W4 / EDGE-E2: no crash on write failure."""
        # Point at a path whose parent doesn't exist AND can't be created
        # (= use /dev/null which is a character device)
        p = Path("/dev/null/impossible/roi.jsonl")
        r = roi_row(ts=1, pass_id="p", slot="gig", budget="LIGHT", picked=None, outcome="x")
        result = append_roi_row(p, r)
        assert result["ok"] is False
        assert "status" in result

    def test_row_ends_with_newline(self, tmp_path):
        """Each JSON line must be newline-terminated so readers can split reliably."""
        p = tmp_path / "roi.jsonl"
        r = roi_row(ts=1, pass_id="p", slot="gig", budget="LIGHT", picked=None, outcome="ok")
        append_roi_row(p, r)
        assert p.read_bytes().endswith(b"\n")
