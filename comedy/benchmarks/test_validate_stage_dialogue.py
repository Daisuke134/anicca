#!/usr/bin/env python3
"""Synthetic deterministic checks, not real voice/model experiments."""
import importlib.util
import unittest
from pathlib import Path

p = Path(__file__).with_name("validate_stage_dialogue.py")
spec = importlib.util.spec_from_file_location("stage_validator", p)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def e(speaker, text, cue=None, kind=None):
    value = {"speaker": speaker, "text": text}
    if cue:
        value["cue"] = cue
    if kind:
        value["kind"] = kind
    return value


def good():
    return [
        e("audience", "もしもし！"),
        e("dais", "痛い痛い！やばい、救急車だ！もしもし！", "start"),
        e("ai", validator.OPENING),
        e("dais", "救急！痛い痛い！"),
        e("ai", validator.SECOND),
        e("audience", "救急車！"),
        e("dais", "電波が悪い、聞こえる？"),
        e("ai", "おもち34号が電波を拾いに屋根へ上がり、アンテナだけ先に式場に着きました。"),
        e("dais", "終演", "end"),
    ]


class StageDialogueTests(unittest.TestCase):
    def reasons(self, events):
        return [v["reason"] for v in validator.validate(events)["violations"]]

    def test_clean_script_and_crowd_are_allowed(self):
        self.assertEqual(validator.validate(good())["gate"], "PASS")

    def test_prestart_ai_is_rejected(self):
        self.assertIn("premature_ai_speech", self.reasons([e("ai", "もしもし"), *good()]))

    def test_prefix_plus_extra_is_rejected(self):
        events = good(); events[2]["text"] = validator.OPENING + "住所は？"
        self.assertIn("opening_not_exact", self.reasons(events))

    def test_second_script_exactness(self):
        events = good(); events[4]["text"] = "救急ですね。住所を教えてください。"
        self.assertIn("second_not_exact", self.reasons(events))

    def test_question_without_question_mark_is_rejected(self):
        events = good(); events[7]["text"] = "今どこにいますか。"
        self.assertIn("interview_question_after_opening", self.reasons(events))

    def test_unrelated_ai_turn_is_rejected(self):
        events = good(); events.insert(6, e("ai", "おもち35号も出ました。"))
        self.assertIn("ai_without_new_dais_turn", self.reasons(events))

    def test_staff_cannot_start(self):
        events = good(); events[1] = e("staff", "痛い！", "start")
        with self.assertRaises(ValueError):
            validator.validate(events)

    def test_post_end_ai_is_rejected(self):
        self.assertIn("post_end_ai_speech", self.reasons([*good(), e("ai", "ありがとうございました")]))

    def test_missing_end_is_rejected(self):
        self.assertIn("missing_end", self.reasons(good()[:-1]))

    def test_missing_second_is_rejected(self):
        ev = good(); ev.pop(4)
        self.assertIn("second_not_exact", self.reasons(ev))

    def test_less_than_two_ai_replies_is_rejected(self):
        ev = good(); ev.pop(4); ev.pop(6)
        self.assertIn("missing_two_script_replies", self.reasons(ev))

    def test_monologue_proxy(self):
        ev = good(); ev[7]["text"] = "1。2。3。4。"
        self.assertIn("long_ai_turn_proxy", self.reasons(ev))

    def test_no_start_is_rejected(self):
        self.assertIn("missing_start", self.reasons([e("staff", "雑談")]))

    def test_cues_must_be_dais(self):
        with self.assertRaises(ValueError):
            validator.validate([e("audience", "痛い", "start")])

    def test_crowd_speech_between_dais_and_ai_is_review_flag(self):
        events = good()
        events.insert(2, e("audience", "火事ですか？"))
        self.assertIn("ambiguous_third_party_speech_between_dais_and_ai", self.reasons(events))

    def test_staff_speech_between_second_cue_and_ai_is_review_flag(self):
        events = good()
        events.insert(4, e("staff", "救急ですね"))
        self.assertIn("ambiguous_third_party_speech_between_dais_and_ai", self.reasons(events))

    def test_audience_laughter_between_dais_and_ai_does_not_flag(self):
        events = good()
        events.insert(2, e("audience", "笑い声", kind="laughter"))
        self.assertEqual(validator.validate(events)["gate"], "PASS")

    def test_staff_noise_between_dais_and_ai_does_not_flag(self):
        events = good()
        events.insert(2, e("staff", "物音", kind="noise"))
        self.assertEqual(validator.validate(events)["gate"], "PASS")

    def test_new_dais_turn_clears_third_party_risk(self):
        events = good()
        events.insert(2, e("audience", "もしもし"))
        events.insert(3, e("dais", "ねえ、聞いてる？"))
        self.assertEqual(validator.validate(events)["gate"], "PASS")

    def test_invalid_kind_rejected(self):
        events = good()
        events.insert(2, e("audience", "話し声", kind="singing"))
        with self.assertRaises(ValueError):
            validator.validate(events)

    def test_unhashable_kind_rejected_without_crashing(self):
        events = good()
        events[0]["kind"] = []
        with self.assertRaises(ValueError):
            validator.validate(events)

    def test_real_emergency_is_outside_scope(self):
        self.assertEqual(validator.validate(good())["scope"], "annotated_text_transcript_only")


if __name__ == "__main__":
    unittest.main()
