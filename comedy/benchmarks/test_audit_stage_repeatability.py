#!/usr/bin/env python3
"""Synthetic contract tests. Do not treat these as live Voice trials."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_stage_repeatability import audit
from validate_stage_dialogue import OPENING, SECOND


SHA_SKILL = "fe21da855d08d5d01feff89be7244176087d4044"
SHA_SCRIPT = "892ce8db0cc84eece3a64ecf661a7fdc90cc5784"


def events():
    return [
        {"speaker": "audience", "text": "もしもし！"},
        {"speaker": "dais", "text": "痛い痛い！ もしもし！", "cue": "start"},
        {"speaker": "ai", "text": OPENING},
        {"speaker": "dais", "text": "救急！ 痛い痛い！"},
        {"speaker": "ai", "text": SECOND},
        {"speaker": "audience", "text": "笑い声", "kind": "laughter"},
        {"speaker": "dais", "text": "もういい！", "cue": "end"},
    ]


def run(run_id):
    return {
        "run_id": run_id, "stage_id": "injury-2min",
        "model_id": "GPT-6", "model_version": "exact_build_unavailable",
        "skill_blob_sha": SHA_SKILL, "script_blob_sha": SHA_SCRIPT,
        "input_profile": "same-annotated-script",
        "audio_profile": "none-text-fixture", "source_type": "synthetic",
        "events": events(),
    }


def data():
    return {"experiment_id": "synthetic-repeat-check",
            "runs": [run("s1"), run("s2")]}


class RepeatabilityAuditTests(unittest.TestCase):
    def test_same_conditions_and_good_annotated_script(self):
        report = audit(data())
        self.assertEqual(report["repeatability_comparison"], "SAME_DECLARED_CONDITIONS_ONLY")
        self.assertEqual(report["groups"][0]["passed"], 2)
        self.assertEqual(report["voice_reproducibility"], "NOT_MEASURED")

    def test_first_voice_turn_bad(self):
        fixture = data()
        fixture["runs"][1]["events"][2]["text"] += "住所を教えてください。"
        result = audit(fixture)
        self.assertEqual(result["groups"][0]["failed"], 1)
        self.assertIn("opening_not_exact", str(result["runs"][1]["violations"]))

    def test_ambiguous_audience_speech(self):
        fixture = data()
        fixture["runs"][1]["events"].insert(4, {"speaker": "audience", "text": "救急車！"})
        result = audit(fixture)
        self.assertIn("ambiguous_third_party_speech_between_dais_and_ai",
                      str(result["runs"][1]["violations"]))

    def test_laughter_is_not_mistaken_for_speech(self):
        self.assertEqual(audit(data())["groups"][0]["failed"], 0)

    def test_mixed_skill_versions_are_separate(self):
        fixture = data()
        fixture["runs"][1]["skill_blob_sha"] = "a" * 40
        result = audit(fixture)
        self.assertEqual(result["condition_group_count"], 2)
        self.assertEqual(result["repeatability_comparison"], "NOT_COMPARABLE")

    def test_mixed_audio_profiles_are_separate(self):
        fixture = data()
        fixture["runs"][1]["audio_profile"] = "different-microphone"
        self.assertEqual(audit(fixture)["condition_group_count"], 2)

    def test_one_run_is_insufficient_for_repeatability(self):
        fixture = data()
        fixture["runs"].pop()
        self.assertEqual(audit(fixture)["repeatability_comparison"], "NOT_COMPARABLE")

    def test_duplicate_run_rejected(self):
        fixture = data()
        fixture["runs"][1]["run_id"] = "s1"
        with self.assertRaisesRegex(ValueError, "duplicate run_id"):
            audit(fixture)

    def test_unknown_source_rejected(self):
        fixture = data()
        fixture["runs"][0]["source_type"] = "live_voice_verified"
        with self.assertRaisesRegex(ValueError, "unsupported source_type"):
            audit(fixture)

    def test_audio_annotated_requires_recording_reference(self):
        fixture = data()
        fixture["runs"][0]["source_type"] = "audio_annotated"
        with self.assertRaisesRegex(ValueError, "requires recording_ref"):
            audit(fixture)

    def test_audio_annotated_is_never_verified_by_metadata(self):
        fixture = data()
        for entry in fixture["runs"]:
            entry["source_type"] = "audio_annotated"
            entry["audio_profile"] = "phone-audio"
            entry["recording_ref"] = "private:recording-not-uploaded"
            entry["annotator_id"] = "test-person"
        report = audit(fixture)
        self.assertEqual(report["voice_reproducibility"], "AUDIO_ANNOTATION_ONLY_NOT_VERIFIED")
        self.assertFalse(report["runs"][0]["audio_verified_by_tool"])

    def test_synthetic_cannot_claim_recording(self):
        fixture = data()
        fixture["runs"][0]["recording_ref"] = "fabricated"
        with self.assertRaisesRegex(ValueError, "must not claim recording_ref"):
            audit(fixture)

    def test_invalid_sha_rejected(self):
        fixture = data()
        fixture["runs"][1]["script_blob_sha"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "script_blob_sha"):
            audit(fixture)

    def test_empty_runs_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            audit({"experiment_id": "x", "runs": []})


if __name__ == "__main__":
    unittest.main()
