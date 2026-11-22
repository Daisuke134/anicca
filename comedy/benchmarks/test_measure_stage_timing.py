#!/usr/bin/env python3
"""Synthetic timing fixtures only: no recorded audio or live model execution."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from measure_stage_timing import measure
from validate_stage_dialogue import OPENING, SECOND


def event(speaker, text, start, end, cue=None, kind=None):
    row = {"speaker": speaker, "text": text, "start_ms": start, "end_ms": end}
    if cue is not None:
        row["cue"] = cue
    if kind is not None:
        row["kind"] = kind
    return row


def good():
    return [
        event("dais", "痛い痛い！ もしもし！", 0, 1600, "start"),
        event("ai", OPENING, 1800, 2900),
        event("dais", "救急！痛い痛い！", 3000, 3700),
        event("ai", SECOND, 3900, 7900),
        event("dais", "救急車がまだ来ない！", 8100, 9000),
        event("ai", "おもち34号の招待状が消防署に届きました。", 9300, 10300),
        event("dais", "もういい、終わり！", 11000, 11200, "end"),
    ]


class TimingAuditTests(unittest.TestCase):
    def test_clean_transcript_reports_nonreal_metrics(self):
        report = measure(good())
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual(report["reply_gap_median_ms"], 200)
        self.assertEqual(report["reply_gap_p95_nearest_rank_ms"], 300)
        self.assertEqual(report["stage_duration_ms"], 11200)
        self.assertEqual([r["gap_ms"] for r in report["reply_gap_ms"]], [200, 200, 300])
        self.assertFalse(report["raw_audio_verified"])

    def test_threshold_is_explicit_not_a_default(self):
        self.assertEqual(measure(good())["timing_violations"], [])
        report = measure(good(), max_reply_gap_ms=250)
        self.assertEqual(report["gate"], "FAIL")
        self.assertEqual([r["reason"] for r in report["timing_violations"]], ["reply_gap_exceeds_target"])

    def test_ai_interrupting_dais_is_negative_gap(self):
        events = good()
        events[1]["start_ms"] = 1200
        report = measure(events)
        self.assertEqual(report["reply_gap_ms"][0]["gap_ms"], -400)
        self.assertIn("ai_overlaps_dais_speech", [r["reason"] for r in report["timing_violations"]])

    def test_dais_interrupts_ai_is_reported_without_automatic_failure(self):
        events = good()
        events[2]["start_ms"] = 2500
        events[2]["end_ms"] = 3700
        report = measure(events)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["dais_overlap_ai_events"][0]["overlap_ms"], 400)

    def test_crowd_laughter_does_not_reset_reply_pair(self):
        events = good()
        events.insert(1, event("audience", "笑い声", 1620, 1750, kind="laughter"))
        report = measure(events)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["reply_gap_ms"][0]["gap_ms"], 200)

    def test_crowd_speech_is_a_review_flag_not_causal_proof(self):
        events = good()
        events.insert(1, event("audience", "もしもし", 1620, 1750))
        report = measure(events)
        self.assertEqual(report["text_gate"], "FAIL")
        self.assertEqual(report["timing_gate"], "PASS")
        self.assertIn("ambiguous_third_party_speech_between_dais_and_ai",
                      [r["reason"] for r in report["text_violations"]])

    def test_repeated_ai_turn_not_falsely_paired(self):
        events = good()
        events.insert(2, event("ai", "おもち34号追加", 2950, 2980))
        report = measure(events)
        self.assertEqual(report["text_gate"], "FAIL")
        self.assertEqual(len(report["reply_gap_ms"]), 3)

    def test_duration_thresholds_opt_in(self):
        self.assertEqual(measure(good(), min_duration_ms=10000, max_duration_ms=12000)["gate"], "PASS")
        self.assertIn("stage_shorter_than_target",
                      [r["reason"] for r in measure(good(), min_duration_ms=12000)["timing_violations"]])
        self.assertIn("stage_longer_than_target",
                      [r["reason"] for r in measure(good(), max_duration_ms=10000)["timing_violations"]])

    def test_time_fields_must_be_nonnegative_ints(self):
        for bad in (True, 1.2, -1, "10", None):
            with self.subTest(bad=bad):
                events = good()
                events[0]["start_ms"] = bad
                with self.assertRaises(ValueError):
                    measure(events)

    def test_end_before_start_rejected(self):
        events = good()
        events[2]["end_ms"] = 2000
        with self.assertRaises(ValueError):
            measure(events)

    def test_out_of_order_start_rejected(self):
        events = good()
        events[2]["start_ms"] = 100
        with self.assertRaises(ValueError):
            measure(events)

    def test_invalid_thresholds_rejected(self):
        for bad in (-1, True, "100"):
            with self.assertRaises(ValueError):
                measure(good(), max_reply_gap_ms=bad)
        with self.assertRaises(ValueError):
            measure(good(), min_duration_ms=500, max_duration_ms=100)

    def test_missing_start_and_end_remain_text_failures(self):
        self.assertEqual(measure(good()[1:])["gate"], "FAIL")
        self.assertEqual(measure(good()[:-1])["gate"], "FAIL")

    def test_cli_strict_exit_and_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            src, dest = directory / "case.json", directory / "report.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-clean", "provenance": "synthetic", "events": good()},
                                     ensure_ascii=False), encoding="utf-8")
            script = Path(__file__).with_name("measure_stage_timing.py")
            ok = subprocess.run([sys.executable, str(script), "--input", str(src), "--output", str(dest),
                                 "--strict", "--max-reply-gap-ms", "350"], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertEqual(json.loads(dest.read_text())["input_provenance"], "synthetic")
            fail = subprocess.run([sys.executable, str(script), "--input", str(src), "--output", str(dest),
                                   "--strict", "--max-reply-gap-ms", "100"], capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1)


if __name__ == "__main__":
    unittest.main()
