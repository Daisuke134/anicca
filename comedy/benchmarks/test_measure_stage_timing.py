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

    def test_ai_tail_after_dais_end_cue_fails_closed(self):
        events = good()
        events[5]["end_ms"] = 11500  # AI starts before end cue, plays 300 ms after cue finishes.
        report = measure(events)
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual(report["timing_gate"], "FAIL")
        self.assertEqual(report["gate"], "FAIL")
        self.assertEqual(report["ai_audio_after_end_total_ms"], 300)
        self.assertEqual(report["ai_audio_after_end_event_count"], 1)
        self.assertEqual(report["timing_violations"][-1],
                         {"event": 5, "reason": "ai_audio_after_end_cue", "spillover_ms": 300})

    def test_ai_tail_touching_end_boundary_is_not_failure(self):
        events = good()
        events[5]["end_ms"] = 11200
        report = measure(events)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["ai_audio_after_end_total_ms"], 0)

    def test_ai_tail_finishes_before_end_boundary_is_not_failure(self):
        report = measure(good())
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["ai_audio_after_end_event_count"], 0)

    def test_cli_strict_ai_tail_after_end_returns_one(self):
        events = good()
        events[5]["end_ms"] = 11500
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "end_spill.json", Path(tmp) / "out.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-end-spill",
                                       "provenance": "synthetic", "events": events},
                                      ensure_ascii=False), encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).with_name("measure_stage_timing.py")),
                   "--input", str(src), "--output", str(dest), "--strict"]
            run = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertEqual(json.loads(dest.read_text())["ai_audio_after_end_total_ms"], 300)

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

    def test_existing_laughter_when_ai_starts_is_opt_in_gate(self):
        events = good()
        events.insert(3, event("audience", "笑い", 3750, 4050, kind="laughter"))
        report = measure(events)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["annotated_audience_laughter_events"], 1)
        self.assertEqual(report["ai_laughter_overlap_total_ms"], 150)
        self.assertEqual(report["ai_entries_during_laughter"], 1)
        self.assertEqual(report["reply_gap_ms"][1]["gap_ms"], 200)
        gated = measure(events, max_ai_entry_laughter_ms=100)
        self.assertEqual(gated["timing_gate"], "FAIL")
        self.assertEqual(gated["timing_violations"][0]["reason"],
                         "ai_enters_active_audience_laughter")
        self.assertEqual(gated["timing_violations"][0]["entry_overlap_ms"], 150)

    def test_laughter_begins_after_ai_started_not_an_entry_failure(self):
        events = good()
        events.insert(4, event("audience", "笑い", 4000, 4300, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=0)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["ai_laughter_overlap_total_ms"], 300)
        self.assertEqual(report["ai_entries_during_laughter"], 0)

    def test_laughter_ending_at_ai_start_does_not_overlap(self):
        events = good()
        events.insert(3, event("audience", "笑い", 3800, 3900, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=0)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["ai_laughter_overlap_total_ms"], 0)

    def test_overlapping_laughter_labels_are_not_double_counted(self):
        events = good()
        events.insert(3, event("audience", "笑い声一", 3700, 4100, kind="laughter"))
        events.insert(4, event("audience", "笑い声二", 3800, 4300, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=400)
        self.assertEqual(report["timing_gate"], "PASS")
        self.assertEqual(report["ai_laughter_overlap_total_ms"], 400)
        self.assertEqual(report["annotated_audience_laughter_events"], 2)
        self.assertEqual(report["ai_entries_during_laughter"], 1)
        self.assertEqual(measure(events, max_ai_entry_laughter_ms=399)["timing_gate"], "FAIL")

    def test_continuous_laughter_labels_crossing_ai_start_are_one_entry(self):
        events = good()
        # Laugh A is active at AI entry (3900); laugh B begins at 3925
        # before A stops (3950), extending the same continuous episode.
        events.insert(3, event("audience", "笑いA", 3750, 3950, kind="laughter"))
        events.insert(5, event("audience", "笑いB", 3925, 4100, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=100)
        self.assertEqual(report["ai_laughter_overlaps"][0]["overlap_ms"], 200)
        self.assertEqual(report["ai_laughter_overlaps"][0]["entry_during_laughter_ms"], 200)
        self.assertEqual(report["ai_entries_during_laughter"], 1)
        self.assertEqual(report["timing_gate"], "FAIL")
        self.assertEqual(measure(events, max_ai_entry_laughter_ms=200)["gate"], "PASS")

    def test_separated_laughter_after_ai_start_is_not_entry(self):
        events = good()
        events.insert(3, event("audience", "笑いA", 3750, 3950, kind="laughter"))
        events.insert(5, event("audience", "笑いB", 3970, 4100, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=50)
        self.assertEqual(report["ai_laughter_overlaps"][0]["overlap_ms"], 180)
        self.assertEqual(report["ai_laughter_overlaps"][0]["entry_during_laughter_ms"], 50)
        self.assertEqual(report["timing_gate"], "PASS")

    def test_touching_laughter_labels_count_as_continuous(self):
        events = good()
        events.insert(3, event("audience", "笑いA", 3750, 3950, kind="laughter"))
        events.insert(5, event("audience", "笑いB", 3950, 4100, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=199)
        self.assertEqual(report["ai_laughter_overlaps"][0]["entry_during_laughter_ms"], 200)
        self.assertEqual(report["timing_gate"], "FAIL")

    def test_staff_laughter_is_not_audience_laughter(self):
        events = good()
        events.insert(3, event("staff", "笑い", 3800, 4000, kind="laughter"))
        report = measure(events, max_ai_entry_laughter_ms=0)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["annotated_audience_laughter_events"], 0)

    def test_invalid_laughter_entry_threshold_rejected(self):
        for bad in (-1, True, 1.5, "100"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    measure(good(), max_ai_entry_laughter_ms=bad)

    def test_cli_laughter_entry_gate_is_strict_when_opted_in(self):
        events = good()
        events.insert(3, event("audience", "笑い声", 3750, 4050, kind="laughter"))
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src.json", Path(tmp) / "out.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-laugh", "provenance": "synthetic",
                                       "events": events}, ensure_ascii=False), encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).with_name("measure_stage_timing.py")),
                   "--input", str(src), "--output", str(dest),
                   "--strict", "--max-ai-entry-laughter-ms", "0"]
            fail = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1, fail.stderr)
            self.assertEqual(json.loads(dest.read_text())["ai_entries_during_laughter"], 1)
            self.assertEqual(subprocess.run(cmd[:-1] + ["150"], capture_output=True,
                                            text=True).returncode, 0)

    def test_second_ai_onset_is_observable_proxy_not_a_laugh(self):
        report = measure(good())
        self.assertEqual(report["second_ai_onset_ms"], 3900)
        self.assertEqual(report["second_ai_onset_is_laughter"], "NOT_MEASURED")
        self.assertEqual(report["thresholds_ms"]["max_second_ai_onset_ms"], None)

    def test_second_ai_onset_target_is_opt_in_and_strict_boundary(self):
        self.assertEqual(measure(good(), max_second_ai_onset_ms=3900)["gate"], "PASS")
        report = measure(good(), max_second_ai_onset_ms=3899)
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual(report["timing_gate"], "FAIL")
        self.assertEqual(report["timing_violations"][0]["reason"], "second_ai_onset_exceeds_target")
        self.assertEqual(report["timing_violations"][0]["onset_ms"], 3900)

    def test_missing_second_ai_turn_is_not_fabricated(self):
        events = [good()[0], good()[1], good()[-1]]
        report = measure(events, max_second_ai_onset_ms=30000)
        self.assertIsNone(report["second_ai_onset_ms"])
        self.assertEqual(report["text_gate"], "FAIL")
        self.assertEqual(report["gate"], "FAIL")

    def test_invalid_second_ai_onset_limits_rejected(self):
        for bad in (-1, True, "30000", 0.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                measure(good(), max_second_ai_onset_ms=bad)

    def test_cli_strict_second_ai_onset_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "onset.json", Path(tmp) / "result.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-second-onset",
                                       "provenance": "synthetic", "events": good()},
                                      ensure_ascii=False), encoding="utf-8")
            command = [sys.executable, str(Path(__file__).with_name("measure_stage_timing.py")),
                       "--input", str(src), "--output", str(dest), "--strict",
                       "--max-second-ai-onset-ms"]
            fail = subprocess.run(command + ["3899"], capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1, fail.stderr)
            self.assertEqual(json.loads(dest.read_text())["second_ai_onset_ms"], 3900)
            ok = subprocess.run(command + ["3900"], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)

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


    def test_ai_turn_duration_is_reported_without_default_failure(self):
        report = measure(good())
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual([v["duration_ms"] for v in report["ai_turn_duration_ms"]],
                         [1100, 4000, 1000])
        self.assertEqual(report["ai_turn_duration_max_ms"], 4000)
        self.assertIsNone(report["thresholds_ms"]["max_ai_turn_duration_ms"])
        self.assertEqual(report["voice_delivery_quality"], "NOT_MEASURED")

    def test_ai_turn_duration_strict_boundary(self):
        self.assertEqual(measure(good(), max_ai_turn_duration_ms=4000)["gate"], "PASS")
        report = measure(good(), max_ai_turn_duration_ms=3999)
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual(report["timing_gate"], "FAIL")
        self.assertEqual(report["timing_violations"],
                         [{"event": 3, "reason": "ai_turn_exceeds_duration_target",
                           "duration_ms": 4000}])

    def test_ai_turn_duration_zero_and_invalid_thresholds(self):
        for bad in (-1, True, False, "4000", 0.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                measure(good(), max_ai_turn_duration_ms=bad)
        self.assertEqual(measure(good(), max_ai_turn_duration_ms=0)["timing_gate"], "FAIL")

    def test_long_ai_one_sentence_detected_without_period_heuristic(self):
        events = good()
        # One long single-sentence AI turn, which the punctuation-count proxy misses.
        events[5]["end_ms"] = 10900
        report = measure(events, max_ai_turn_duration_ms=1500)
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual(report["timing_gate"], "FAIL")
        self.assertIn({"event": 5, "reason": "ai_turn_exceeds_duration_target",
                       "duration_ms": 1600}, report["timing_violations"])

    def test_cli_strict_ai_turn_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "turn-budget.json", Path(tmp) / "report.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-ai-turn-budget",
                                       "provenance": "synthetic", "events": good()},
                                      ensure_ascii=False), encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).with_name("measure_stage_timing.py")),
                   "--input", str(src), "--output", str(dest), "--strict",
                   "--max-ai-turn-duration-ms"]
            failed = subprocess.run(cmd + ["3999"], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1, failed.stderr)
            self.assertEqual(json.loads(dest.read_text())["ai_turn_duration_max_ms"], 4000)
            passed = subprocess.run(cmd + ["4000"], capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_aggregate_talk_share_reports_without_default_gate(self):
        report = measure(good())
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["ai_stage_speaking_ms"], 6100)
        self.assertEqual(report["dais_stage_speaking_ms"], 3400)
        self.assertAlmostEqual(report["ai_talk_share_percent"], 64.211, places=3)
        self.assertIsNone(report["thresholds_ms"]["max_ai_talk_share_percent"])
        self.assertEqual(report["ai_talk_share_is_laughter"], "NOT_MEASURED")

    def test_many_short_ai_turns_collectively_dominate_despite_per_turn_pass(self):
        # No AI turn exceeds 5s, but the total speaking-time share exceeds 60%.
        report = measure(good(), max_ai_turn_duration_ms=5000, max_ai_talk_share_percent=60)
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual(report["timing_gate"], "FAIL")
        self.assertIn("ai_dominates_speaking_time",
                      [r["reason"] for r in report["timing_violations"]])
        self.assertEqual(measure(good(), max_ai_talk_share_percent=65)["gate"], "PASS")

    def test_ai_talk_share_excludes_post_end_audio_from_fraction(self):
        events = good()
        events[5]["end_ms"] = 11500
        report = measure(events)
        self.assertEqual(report["ai_audio_after_end_total_ms"], 300)
        self.assertEqual(report["ai_stage_speaking_ms"], 7000)
        self.assertEqual(report["dais_stage_speaking_ms"], 3400)

    def test_invalid_ai_talk_share_limit_rejected(self):
        for bad in (-1, True, False, "60", 60.5, 101):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                measure(good(), max_ai_talk_share_percent=bad)

    def test_cli_strict_ai_talk_share_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "talk.json", Path(tmp) / "report.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-share",
                                       "provenance": "synthetic", "events": good()},
                                      ensure_ascii=False), encoding="utf-8")
            command = [sys.executable, str(Path(__file__).with_name("measure_stage_timing.py")),
                       "--input", str(src), "--output", str(dest),
                       "--strict", "--max-ai-talk-share-percent"]
            fail = subprocess.run(command + ["64"], capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1, fail.stderr)
            self.assertEqual(json.loads(dest.read_text())["ai_stage_speaking_ms"], 6100)
            passed = subprocess.run(command + ["65"], capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)


class DaisReentryGapTests(unittest.TestCase):
    """Timestamp-only proxy for room before Dais's next spoken reaction."""

    def test_reports_gap_without_automatic_stage_policy(self):
        r = measure(good())
        self.assertEqual([x["gap_ms"] for x in r["dais_reentry_gap_ms"]], [100, 200])
        self.assertEqual(r["dais_reentry_gap_median_ms"], 150)
        self.assertEqual(r["dais_reentry_is_physical_acting"], "NOT_MEASURED")
        self.assertEqual(r["gate"], "PASS")
        self.assertIsNone(r["thresholds_ms"]["min_dais_reentry_gap_ms"])

    def test_opt_in_boundary_uses_strict_below_not_equal(self):
        self.assertEqual(measure(good(), min_dais_reentry_gap_ms=100)["gate"], "PASS")
        r = measure(good(), min_dais_reentry_gap_ms=101)
        self.assertEqual(r["text_gate"], "PASS")
        self.assertEqual(r["timing_gate"], "FAIL")
        self.assertEqual([x["reason"] for x in r["timing_violations"]],
                         ["dais_reentry_below_opt_in_target"])
        self.assertEqual(r["timing_violations"][0]["gap_ms"], 100)

    def test_overlapping_dais_reply_is_negative_gap_not_default_failure(self):
        events = good()
        events[2]["start_ms"] = 2500
        r = measure(events)
        self.assertEqual(r["dais_reentry_gap_ms"][0]["gap_ms"], -400)
        self.assertEqual(r["timing_gate"], "PASS")
        self.assertEqual(measure(events, min_dais_reentry_gap_ms=0)["timing_gate"], "FAIL")

    def test_laughter_is_not_a_dais_reply(self):
        events = good()
        events.insert(2, event("audience", "笑い", 2920, 2980, kind="laughter"))
        r = measure(events)
        self.assertEqual([x["gap_ms"] for x in r["dais_reentry_gap_ms"]], [100, 200])
        self.assertEqual(len(r["dais_reentry_gap_ms"]), 2)

    def test_final_end_cue_excluded(self):
        r = measure(good())
        self.assertEqual(len(r["dais_reentry_gap_ms"]), 2)
        self.assertNotIn(700, [x["gap_ms"] for x in r["dais_reentry_gap_ms"]])

    def test_post_end_debrief_does_not_count_as_stage_reentry(self):
        events = good() + [event("dais", "はい、稽古ここまで。", 11400, 11900)]
        report = measure(events)
        self.assertEqual(report["text_gate"], "PASS")
        self.assertEqual([r["gap_ms"] for r in report["dais_reentry_gap_ms"]], [100, 200])
        self.assertEqual(report["dais_reentry_gap_median_ms"], 150)

    def test_post_end_debrief_cannot_trigger_opt_in_gap_failure(self):
        events = good() + [event("dais", "お疲れさま。", 11400, 12000)]
        report = measure(events, min_dais_reentry_gap_ms=1200)
        # Two genuine stage replies are short; a debrief must not be a THIRD violation.
        self.assertEqual(len(report["dais_reentry_gap_ms"]), 2)
        self.assertEqual([v["reason"] for v in report["timing_violations"]],
                         ["dais_reentry_below_opt_in_target"] * 2)

    def test_end_cue_then_late_debrief_excluded_even_if_commentary_overlaps_ai_tail(self):
        events = good()
        events[5]["end_ms"] = 11500
        events.append(event("dais", "音の確認をします。", 11400, 11800))
        report = measure(events)
        self.assertEqual(len(report["dais_reentry_gap_ms"]), 2)
        self.assertEqual(report["ai_audio_after_end_total_ms"], 300)
        self.assertEqual(report["timing_gate"], "FAIL")

    def test_minimum_validation(self):
        for bad in (-1, True, 1.2, "100"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    measure(good(), min_dais_reentry_gap_ms=bad)

    def test_cli_opt_in_strict_exit_and_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "input.json", Path(tmp) / "out.json"
            src.write_text(json.dumps({"scenario_id": "synthetic-reentry",
                                       "provenance": "synthetic", "events": good()},
                                      ensure_ascii=False), encoding="utf-8")
            cmd = [sys.executable, str(Path(__file__).with_name("measure_stage_timing.py")),
                   "--input", str(src), "--output", str(dest),
                   "--min-dais-reentry-gap-ms", "101", "--strict"]
            p = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(p.returncode, 1, p.stderr)
            report = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(report["dais_reentry_gap_median_ms"], 150)
            self.assertEqual(report["timing_gate"], "FAIL")


if __name__ == "__main__":
    unittest.main()
