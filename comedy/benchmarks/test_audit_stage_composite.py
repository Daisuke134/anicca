#!/usr/bin/env python3
"""Regression tests: isolated green gates must not mask another red gate."""
import copy
import unittest
from audit_stage_composite import evaluate, run


def fixture():
    events = [
        {"speaker": "dais", "text": "痛い痛い！もしもし！", "cue": "start"},
        {"speaker": "ai", "text": "はい、救急指令センターです。火事ですか、救急ですか？"},
        {"speaker": "dais", "text": "救急！痛い痛い！"},
        {"speaker": "ai", "text": "救急ですね。声で分かりました。右ひざがご実家に帰られています。病名は「急性ひざの里帰りスペシャル」です。帰りの切符はこちらで手配します。"},
        {"speaker": "dais", "text": "救急車はどうした！"},
        {"speaker": "ai", "text": "おもち34号は式場で新郎の送迎係になりました。"},
        {"speaker": "dais", "text": "僕の迎えは？"},
        {"speaker": "ai", "text": "右折田まっすぐが駐車場を四周しています。"},
        {"speaker": "dais", "text": "おもち34号はまだ？",
         "anchor_any": ["おもち34号"], "action_any": ["手配"]},
        {"speaker": "ai", "text": "おもち34号は新婚旅行の荷物として空港にいます。別便を手配しました。"},
        {"speaker": "dais", "text": "終演", "cue": "end"},
    ]
    chains = [{"setup_ai_event": 5, "callback_ai_event": 9, "entity": "おもち34号",
               "setup_any": ["式場"], "payoff_any": ["新婚旅行"],
               "forbidden_after_setup": ["おもち34号が到着しました"]}]
    return events, chains


class CompositeTests(unittest.TestCase):
    def test_all_three_gates_pass(self):
        e, c = fixture()
        r = evaluate(e, c, require_adlib=True)
        self.assertEqual(r["gate"], "PASS")
        self.assertEqual(set(r["component_gates"].values()), {"PASS"})
        self.assertEqual(r["real_voice"], "NOT_MEASURED")

    def test_bad_first_line_cannot_hide_under_callback_pass(self):
        e, c = fixture()
        e[1]["text"] = "はい、救急車です。住所はどこ？"
        r = evaluate(e, c)
        self.assertEqual(r["component_gates"]["multi_turn_callback"], "PASS")
        self.assertEqual(r["component_gates"]["script_and_cues"], "FAIL")
        self.assertEqual(r["gate"], "FAIL")

    def test_bad_second_line_fails(self):
        e, c = fixture()
        e[3]["text"] = "救急ですね。住所を教えてください。"
        self.assertEqual(evaluate(e, c)["gate"], "FAIL")

    def test_missing_callback_cannot_hide_under_stage_pass(self):
        e, c = fixture()
        e[9]["text"] = "おもち34号は式場に残りました。別便を手配しました。"
        r = evaluate(e, c)
        self.assertEqual(r["component_gates"]["script_and_cues"], "PASS")
        self.assertEqual(r["component_gates"]["multi_turn_callback"], "FAIL")
        self.assertEqual(r["gate"], "FAIL")

    def test_uncommitted_action_cannot_hide_under_callback_pass(self):
        e, c = fixture()
        e[9]["text"] = "おもち34号は新婚旅行の荷物です。別便を手配する予定です。"
        r = evaluate(e, c, require_adlib=True)
        self.assertEqual(r["component_gates"]["script_and_cues"], "PASS")
        self.assertEqual(r["component_gates"]["multi_turn_callback"], "PASS")
        self.assertEqual(r["component_gates"]["adlib_uptake"], "FAIL")
        self.assertEqual(r["gate"], "FAIL")

    def test_third_party_interruption_requires_review(self):
        e, c = fixture()
        e.insert(9, {"speaker": "audience", "kind": "speech", "text": "こっち見て！"})
        c[0]["callback_ai_event"] = 10
        r = evaluate(e, c)
        self.assertEqual(r["component_gates"]["script_and_cues"], "FAIL")
        self.assertEqual(r["gate"], "FAIL")

    def test_audience_laughter_not_interruption(self):
        e, c = fixture()
        e.insert(9, {"speaker": "audience", "kind": "laughter", "text": "笑"})
        c[0]["callback_ai_event"] = 10
        self.assertEqual(evaluate(e, c, require_adlib=True)["gate"], "PASS")

    def test_ending_not_optional(self):
        e, c = fixture()
        e.pop()
        self.assertEqual(evaluate(e, c)["component_gates"]["script_and_cues"], "FAIL")

    def test_unrequested_adlib_is_not_mislabeled_pass(self):
        e, c = fixture()
        del e[8]["anchor_any"]
        del e[8]["action_any"]
        r = evaluate(e, c)
        self.assertEqual(r["gate"], "PASS")
        self.assertEqual(r["component_gates"]["adlib_uptake"], "NOT_REQUESTED")

    def test_required_adlib_without_annotations_rejected(self):
        e, c = fixture()
        del e[8]["anchor_any"]
        del e[8]["action_any"]
        with self.assertRaises(ValueError):
            evaluate(e, c, require_adlib=True)

    def test_invalid_synthetic_input_rejected(self):
        e, c = fixture()
        with self.assertRaises(ValueError):
            run({"source_type": "audio_annotated", "cases": [
                {"events": e, "chains": c, "expected_gate": "PASS"}]})

    def test_wrong_cue_speaker_rejected(self):
        e, c = fixture()
        e[0]["speaker"] = "audience"
        with self.assertRaises(ValueError):
            evaluate(e, c)

    def test_synthetic_suite(self):
        data = scenarios()
        r = run(data)
        self.assertTrue(r["all_expectations_met"])
        self.assertEqual(r["total_cases"], 8)


def scenarios():
    base, chains = fixture()
    cases = [{"scenario_id": "all-three-pass", "events": base, "chains": chains,
              "require_adlib": True, "expected_gate": "PASS"}]

    def change(name, update, expected="FAIL"):
        e, c = copy.deepcopy(base), copy.deepcopy(chains)
        update(e, c)
        cases.append({"scenario_id": name, "events": e, "chains": c,
                      "require_adlib": True, "expected_gate": expected})

    change("bad-first-line", lambda e, c: e[1].update(text="住所を教えてください。"))
    change("bad-second-line", lambda e, c: e[3].update(text="住所はどこですか？"))
    change("missing-callback", lambda e, c: e[9].update(text="おもち34号は式場に残りました。別便を手配しました。"))
    change("uncommitted-adlib", lambda e, c: e[9].update(text="おもち34号は新婚旅行の荷物です。別便を手配する予定です。"))
    def third_party(e, c):
        e.insert(9, {"speaker": "audience", "kind": "speech", "text": "AIこっち！"})
        c[0]["callback_ai_event"] += 1
    change("third-party-speaks", third_party)
    change("missing-end", lambda e, c: e.pop())
    def harmless_laugh(e, c):
        e.insert(9, {"speaker": "audience", "kind": "laughter", "text": "笑"})
        c[0]["callback_ai_event"] += 1
    change("audience-laughter-only", harmless_laugh, "PASS")
    return {"source_type": "synthetic", "cases": cases}


if __name__ == "__main__":
    unittest.main()
