#!/usr/bin/env python3
"""Regression cases for complete-turn setup/reaction/callback continuity."""
import copy
import unittest

from audit_callback_continuity import audit, run


def fixture():
    events = [
        {"speaker": "dais", "text": "痛い、もしもし！", "cue": "start"},
        {"speaker": "ai", "text": "はい、救急指令センターです。火事ですか、救急ですか？"},
        {"speaker": "dais", "text": "救急です！"},
        {"speaker": "ai", "text": "救急ですね。声で分かりました。右ひざがご実家に帰られています。病名は「急性ひざの里帰りスペシャル」です。帰りの切符はこちらで手配します。"},
        {"speaker": "dais", "text": "おもち34号は？"},
        {"speaker": "ai", "text": "おもち34号は式場で新郎の送迎係に任命されました。"},
        {"speaker": "dais", "text": "じゃあ僕の迎えはどうなるの！"},
        {"speaker": "ai", "text": "右折田まっすぐは駐車場を四周しています。"},
        {"speaker": "dais", "text": "おもち34号はまだ？"},
        {"speaker": "ai", "text": "おもち34号は今、新婚旅行の荷物として空港のベルトコンベヤーを回っています。"},
        {"speaker": "dais", "text": "終演", "cue": "end"},
    ]
    chains = [{
        "setup_ai_event": 5,
        "callback_ai_event": 9,
        "entity": "おもち34号",
        "setup_any": ["式場"],
        "payoff_any": ["新婚旅行"],
        "forbidden_after_setup": ["おもち34号が到着しました"],
    }]
    return events, chains


def reasons(events, chains):
    return {x["reason"] for x in audit(events, chains)["violations"]}


class ContinuityAuditTests(unittest.TestCase):
    def test_good_chain(self):
        e, c = fixture()
        self.assertEqual(audit(e, c)["gate"], "PASS")

    def test_setup_character_missing(self):
        e, c = fixture()
        e[5]["text"] = "式場で送迎係になりました。"
        self.assertIn("setup_missing_entity", reasons(e, c))

    def test_setup_state_missing(self):
        e, c = fixture()
        e[5]["text"] = "おもち34号が走っています。"
        self.assertIn("setup_missing_state", reasons(e, c))

    def test_callback_character_missing(self):
        e, c = fixture()
        e[9]["text"] = "救急車は新婚旅行の荷物です。"
        self.assertIn("callback_missing_entity", reasons(e, c))

    def test_callback_payoff_missing(self):
        e, c = fixture()
        e[9]["text"] = "おもち34号です。現在地を確認しました。"
        self.assertIn("callback_missing_payoff", reasons(e, c))

    def test_dais_reaction_required(self):
        e, c = fixture()
        e[6]["speaker"] = "audience"
        e[8]["speaker"] = "staff"
        self.assertIn("no_dais_reaction_between_beats", reasons(e, c))

    def test_arrival_contradiction_detected_later(self):
        e, c = fixture()
        e[9]["text"] += "おもち34号が到着しました。"
        self.assertIn("forbidden_continuity_reversal", reasons(e, c))

    def test_contradiction_in_middle_turn_detected(self):
        e, c = fixture()
        e[7]["text"] = "おもち34号が到着しました。"
        self.assertIn("forbidden_continuity_reversal", reasons(e, c))

    def test_ai_monologue_without_reaction(self):
        e, c = fixture()
        e[6]["speaker"] = "ai"
        self.assertIn("consecutive_ai_turns_without_dais", reasons(e, c))

    def test_ai_speaks_before_cue(self):
        e, c = fixture()
        e.insert(0, {"speaker": "ai", "text": "もしもし。"})
        c[0]["setup_ai_event"] += 1
        c[0]["callback_ai_event"] += 1
        self.assertIn("ai_spoke_before_start", reasons(e, c))

    def test_ai_speaks_after_end(self):
        e, c = fixture()
        e.append({"speaker": "ai", "text": "ありがとうございました。"})
        self.assertIn("ai_spoke_after_end", reasons(e, c))

    def test_audience_laughter_does_not_count_as_dais(self):
        e, c = fixture()
        e.insert(6, {"speaker": "audience", "text": "笑", "kind": "laughter"})
        c[0]["callback_ai_event"] += 1
        self.assertEqual(audit(e, c)["gate"], "PASS")

    def test_missing_start_cue(self):
        e, c = fixture()
        del e[0]["cue"]
        self.assertIn("missing_dais_start_cue", reasons(e, c))

    def test_unannotated_cannot_pass(self):
        e, _ = fixture()
        with self.assertRaises(ValueError):
            audit(e, [])

    def test_wrong_indices_not_silently_scored(self):
        e, c = fixture()
        c[0]["callback_ai_event"] = 7
        self.assertIn("callback_missing_entity", reasons(e, c))
        c[0]["callback_ai_event"] = 200
        with self.assertRaises(ValueError):
            audit(e, c)

    def test_bad_annotations_rejected(self):
        e, c = fixture()
        c[0]["payoff_any"] = []
        with self.assertRaises(ValueError):
            audit(e, c)

    def test_bad_speaker_rejected(self):
        e, c = fixture()
        e[5]["speaker"] = "hallucinated_speaker"
        with self.assertRaises(ValueError):
            audit(e, c)

    def test_runner_refuses_real_audio_claims(self):
        e, c = fixture()
        with self.assertRaises(ValueError):
            run({"source_type": "audio_annotated", "cases": [
                {"events": e, "chains": c, "expected_gate": "PASS"}]})

    def test_synthetic_suite_expected_results(self):
        e, c = fixture()
        bad_e = copy.deepcopy(e)
        bad_e[9]["text"] = "おもち34号が到着しました。"
        result = run({"source_type": "synthetic", "cases": [
            {"scenario_id": "good", "events": e, "chains": c, "expected_gate": "PASS"},
            {"scenario_id": "bad", "events": bad_e, "chains": c, "expected_gate": "FAIL"},
        ]})
        self.assertTrue(result["all_expectations_met"])
        self.assertEqual(result["expectations_met"], 2)
        self.assertEqual(result["voice"], "NOT_MEASURED")


if __name__ == "__main__":
    unittest.main()
