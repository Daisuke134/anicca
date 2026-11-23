#!/usr/bin/env python3
"""Synthetic ASR fragment fixtures only; NOT live Voice performance tests."""
import copy
import unittest

from normalize_asr_turns import evaluate, normalize
from validate_stage_dialogue import OPENING, SECOND, validate


def fixture():
    return {
        "scenario_id": "synthetic-asr-two-voice-replies",
        "provenance": "synthetic",
        "events": [
            {"speaker": "audience", "kind": "noise", "text": "椅子の音", "start_ms": 0, "end_ms": 90},
            {"speaker": "dais", "text": "痛い痛い！ ", "cue": "start",
             "turn_id": "d1", "start_ms": 100, "end_ms": 300},
            {"speaker": "dais", "text": "もしもし！", "turn_id": "d1",
             "start_ms": 305, "end_ms": 500},
            {"speaker": "ai", "text": OPENING[:11], "turn_id": "a1",
             "start_ms": 550, "end_ms": 800},
            {"speaker": "ai", "text": OPENING[11:], "turn_id": "a1",
             "start_ms": 805, "end_ms": 1400},
            {"speaker": "dais", "text": "救急！ ", "turn_id": "d2",
             "start_ms": 1450, "end_ms": 1600},
            {"speaker": "dais", "text": "痛い痛い！", "turn_id": "d2",
             "start_ms": 1605, "end_ms": 1750},
            {"speaker": "ai", "text": SECOND[:24], "turn_id": "a2",
             "start_ms": 1800, "end_ms": 2300},
            {"speaker": "ai", "text": SECOND[24:], "turn_id": "a2",
             "start_ms": 2310, "end_ms": 3100},
            {"speaker": "audience", "kind": "laughter", "text": "笑い声",
             "start_ms": 3200, "end_ms": 3250},
            {"speaker": "dais", "text": "もういい！", "cue": "end", "turn_id": "d3",
             "start_ms": 3300, "end_ms": 3450},
        ],
    }


class NormalizationTests(unittest.TestCase):
    def test_split_opening_and_second_recover_without_editing_text(self):
        data = fixture()
        self.assertEqual(validate(data["events"])["gate"], "FAIL")
        report = evaluate(data)
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["source_chunk_count"], 11)
        self.assertEqual(report["normalized_event_count"], 7)
        self.assertEqual(report["joined_chunk_count"], 4)
        self.assertEqual(report["normalized_events"][2]["text"], OPENING)
        self.assertEqual(report["normalized_events"][4]["text"], SECOND)
        self.assertFalse(report["raw_audio_verified"])

    def test_uninterrupted_laughter_is_preserved_as_event(self):
        result = evaluate(fixture())
        self.assertEqual(result["normalized_events"][5]["kind"], "laughter")
        self.assertEqual(result["audience_laughter"], "NOT_MEASURED")

    def test_unexpected_intervening_audience_speech_causes_review_flag(self):
        data = fixture()
        data["events"].insert(7, {"speaker": "audience", "text": "救急車！",
                                  "start_ms": 1760, "end_ms": 1770})
        report = evaluate(data)
        self.assertEqual(report["gate"], "FAIL")
        self.assertIn("ambiguous_third_party_speech_between_dais_and_ai",
                      str(report["stage_gate"]["violations"]))

    def test_interleaved_third_party_speech_cannot_be_merged_away(self):
        data = fixture()
        data["events"].insert(4, {"speaker": "staff", "text": "それ違う",
                                  "start_ms": 802, "end_ms": 804})
        with self.assertRaisesRegex(ValueError, "noncontiguous reused turn_id"):
            evaluate(data)

    def test_wrong_script_word_still_fails_after_normalization(self):
        data = fixture()
        data["events"][4]["text"] += "住所を教えてください。"
        report = evaluate(data)
        self.assertEqual(report["gate"], "FAIL")
        self.assertIn("opening_not_exact", str(report["stage_gate"]["violations"]))

    def test_missing_turn_id_rejected(self):
        data = fixture()
        data["events"][3].pop("turn_id")
        with self.assertRaisesRegex(ValueError, "missing explicit turn_id"):
            evaluate(data)

    def test_reused_noncontiguous_turn_id_rejected(self):
        data = fixture()
        data["events"][5]["turn_id"] = "d1"
        with self.assertRaisesRegex(ValueError, "noncontiguous reused turn_id"):
            evaluate(data)

    def test_joined_fragments_must_share_speaker(self):
        data = fixture()
        data["events"][4]["speaker"] = "dais"
        with self.assertRaisesRegex(ValueError, "speaker conflict"):
            evaluate(data)

    def test_long_silent_gap_between_fragments_rejected(self):
        data = fixture()
        data["events"][4]["start_ms"] = 1200
        self.assertIn("ambiguous fragment gap", self._error(data))

    def _error(self, payload):
        with self.assertRaises(ValueError) as exc:
            evaluate(payload)
        return str(exc.exception)

    def test_overlapping_chunks_rejected(self):
        data = fixture()
        data["events"][4]["start_ms"] = 750
        self.assertIn("ambiguous fragment gap", self._error(data))

    def test_cue_on_second_fragment_rejected(self):
        data = fixture()
        data["events"][2]["cue"] = "start"
        self.assertIn("invalid cue within a turn", self._error(data))

    def test_boolean_timestamps_rejected(self):
        data = fixture()
        data["events"][2]["start_ms"] = True
        self.assertIn("invalid timestamps", self._error(data))

    def test_negative_gap_threshold_rejected(self):
        with self.assertRaisesRegex(ValueError, "max_gap_ms"):
            normalize(fixture()["events"], max_gap_ms=-1)

    def test_boolean_gap_threshold_rejected(self):
        with self.assertRaisesRegex(ValueError, "max_gap_ms"):
            normalize(fixture()["events"], max_gap_ms=True)

    def test_unknown_provenance_rejected(self):
        data = fixture()
        data["provenance"] = "real_voice_verified"
        with self.assertRaisesRegex(ValueError, "unsupported provenance"):
            evaluate(data)

    def test_audio_annotated_does_not_prove_voice(self):
        data = fixture()
        data["provenance"] = "audio_annotated"
        result = evaluate(data)
        self.assertEqual(result["gate"], "PASS")
        self.assertFalse(result["speaker_identity_verified"])
        self.assertEqual(result["voice_reproducibility"], "NOT_MEASURED")

    def test_end_cue_after_performance_remains_silent(self):
        data = fixture()
        data["events"].append({"speaker": "ai", "text": "ありがとうございました。",
                               "turn_id": "a3", "start_ms": 3500, "end_ms": 3750})
        result = evaluate(data)
        self.assertEqual(result["gate"], "FAIL")
        self.assertIn("post_end_ai_speech", str(result["stage_gate"]["violations"]))


if __name__ == "__main__":
    unittest.main()
