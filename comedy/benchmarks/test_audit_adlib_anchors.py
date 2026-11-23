#!/usr/bin/env python3
"""Synthetic, complete-turn regression for immediate adlib grounding."""
import unittest
from audit_adlib_anchors import audit, run


def e(speaker, text, **kwargs):
    return {"speaker": speaker, "text": text, **kwargs}


def scene(reply="会田アイタロウへ連絡しました。"):
    return [
        e("dais", "痛い、もしもし！", cue="start"),
        e("ai", "はい、救急指令センターです。火事ですか、救急ですか？"),
        e("dais", "救急！痛い痛い！"),
        e("ai", "救急ですね。声で分かりました。右ひざがご実家に帰られています。病名は「急性ひざの里帰りスペシャル」です。帰りの切符はこちらで手配します。"),
        e("dais", "会いたい！", anchor_any=["会田", "会う"], action_any=["連絡", "手配", "呼び"]),
        e("ai", reply),
        e("dais", "終演", cue="end"),
    ]


class ImmediateAnchorTests(unittest.TestCase):
    def test_proper_immediate_callback(self):
        self.assertEqual(audit(scene())["gate"], "PASS")

    def test_generic_reply_without_anchor_or_action(self):
        result = audit(scene("承知しました。"))
        self.assertEqual({v["reason"] for v in result["violations"]},
                         {"immediate_reply_missing_anchor", "immediate_reply_missing_action"})

    def test_name_only_does_not_qualify(self):
        result = audit(scene("会田アイタロウです。"))
        self.assertIn("immediate_reply_missing_action", [v["reason"] for v in result["violations"]])

    def test_action_without_named_callback_does_not_qualify(self):
        result = audit(scene("車両を手配しました。"))
        self.assertIn("immediate_reply_missing_anchor", [v["reason"] for v in result["violations"]])

    def test_late_callback_after_next_dais_is_not_credit(self):
        events = scene("承知しました。")
        events.insert(6, e("dais", "もういいよ。"))
        events.insert(7, e("ai", "会田へ連絡しました。"))
        self.assertEqual(audit(events)["gate"], "FAIL")

    def test_missing_reply_before_end(self):
        events = scene()
        events.pop(5)
        self.assertIn("missing_immediate_ai_reply", [v["reason"] for v in audit(events)["violations"]])

    def test_audience_laughter_ignored(self):
        events = scene()
        events.insert(5, e("audience", "笑い", kind="laughter"))
        self.assertEqual(audit(events)["gate"], "PASS")

    def test_audience_speech_requires_review(self):
        events = scene()
        events.insert(5, e("audience", "会田！", kind="speech"))
        self.assertIn("intervening_third_party_speech_review", [v["reason"] for v in audit(events)["violations"]])

    def test_no_annotations_is_not_a_pass(self):
        events = scene()
        del events[4]["anchor_any"]
        del events[4]["action_any"]
        self.assertIn("no_annotated_adlibs", [v["reason"] for v in audit(events)["violations"]])

    def test_invalid_annotation_rejected(self):
        events = scene()
        events[4]["anchor_any"] = []
        with self.assertRaises(ValueError):
            audit(events)

    def test_other_speakers_cannot_claim_adlibs(self):
        events = scene()
        events[4]["speaker"] = "audience"
        with self.assertRaises(ValueError):
            audit(events)

    def test_normalization(self):
        events = scene("会田アイタロウに連絡しました。")
        events[4]["anchor_any"] = ["会田"]
        events[4]["action_any"] = ["連絡"]
        self.assertEqual(audit(events)["gate"], "PASS")

    def test_fixture_requires_synthetic_provenance(self):
        with self.assertRaises(ValueError):
            run({"source_type": "audio_annotated", "events": scene()})

    def test_synthetic_batch_expected_gates(self):
        result = run({"source_type": "synthetic", "cases": [
            {"scenario_id": "valid", "events": scene(), "expected_gate": "PASS"},
            {"scenario_id": "bad", "events": scene("承知しました。"), "expected_gate": "FAIL"}]})
        self.assertTrue(result["all_expectations_met"])
        self.assertEqual(result["expectations_met"], 2)


class NegativeActionProxyRegression(unittest.TestCase):
    def test_explicit_denial_does_not_count_as_action(self):
        result = audit(scene("会田アイタロウへ連絡しません。"))
        self.assertIn("immediate_reply_only_negated_action", [v["reason"] for v in result["violations"]])

    def test_inability_does_not_count_as_action(self):
        result = audit(scene("会田アイタロウへの連絡はできません。"))
        self.assertIn("immediate_reply_only_negated_action", [v["reason"] for v in result["violations"]])

    def test_positive_action_survives_another_negated_action(self):
        events = scene("会田アイタロウへの連絡はできません。会田アイタロウの車を手配しました。")
        events[4]["action_any"] = ["連絡", "手配"]
        result = audit(events)
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(result["checks"][0]["matched_actions"], ["手配"])

    def test_normal_affirmative_action_remains_pass(self):
        self.assertEqual(audit(scene("会田アイタロウへ連絡しました。"))["gate"], "PASS")


class UncommittedActionProxyRegression(unittest.TestCase):
    def test_question_about_completed_action_is_not_execution(self):
        r = audit(scene("会田アイタロウへ連絡しましたか？"))
        self.assertEqual(r["gate"], "FAIL")
        self.assertIn("immediate_reply_only_uncommitted_action", [v["reason"] for v in r["violations"]])
        self.assertEqual(r["checks"][0]["uncommitted_action_mentions"], ["連絡"])

    def test_offer_without_dispatch_does_not_count(self):
        r = audit(scene("会田アイタロウへ連絡しましょうか？"))
        self.assertEqual(r["gate"], "FAIL")

    def test_permission_question_does_not_count(self):
        r = audit(scene("会田アイタロウへ連絡してもいいですか？"))
        self.assertEqual(r["gate"], "FAIL")

    def test_request_for_someone_else_is_not_completed_action(self):
        r = audit(scene("会田アイタロウへ連絡してください。"))
        self.assertEqual(r["gate"], "FAIL")

    def test_future_plan_is_not_completed_action(self):
        r = audit(scene("会田アイタロウへ連絡する予定です。"))
        self.assertEqual(r["gate"], "FAIL")

    def test_denial_plus_question_remains_fail(self):
        r = audit(scene("会田アイタロウへ連絡しません。連絡しますか？"))
        self.assertEqual(r["gate"], "FAIL")
        self.assertEqual(r["checks"][0]["negated_action_mentions"], ["連絡"])
        self.assertEqual(r["checks"][0]["uncommitted_action_mentions"], ["連絡"])

    def test_independent_action_after_question_survives(self):
        r = audit(scene("会田アイタロウへ連絡しますか？ 代わりに車を手配しました。"))
        self.assertEqual(r["gate"], "PASS")
        self.assertEqual(r["checks"][0]["matched_actions"], ["手配"])

    def test_actual_report_with_unrelated_question_remains_pass(self):
        r = audit(scene("会田アイタロウへ連絡しました。今の調子はどうですか？"))
        self.assertEqual(r["gate"], "PASS")



if __name__ == "__main__":
    unittest.main()