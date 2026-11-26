#!/usr/bin/env python3
"""Regression for text-length proxy that protects a live human reply slot."""
import unittest

from validate_stage_dialogue import validate
from audit_stage_composite import evaluate
from test_audit_stage_composite import fixture


class HumanReplyBudgetTests(unittest.TestCase):
    def test_existing_stage_turns_remain_pass(self):
        events, chains = fixture()
        result = evaluate(events, chains, require_adlib=True)
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(result["stage"]["max_ai_turn_chars"], 96)
        self.assertEqual(result["real_voice"], "NOT_MEASURED")

    def test_one_long_sentence_fails_composite_not_callback(self):
        events, chains = fixture()
        events[7]["text"] = "右折田まっすぐは" + "右折" * 54 + "しています。"
        result = evaluate(events, chains, require_adlib=True)
        self.assertEqual(result["component_gates"]["multi_turn_callback"], "PASS")
        self.assertEqual(result["component_gates"]["script_and_cues"], "FAIL")
        self.assertIn("ai_turn_exceeds_char_budget_proxy",
                      [v["reason"] for v in result["stage"]["violations"]])
        self.assertEqual(result["gate"], "FAIL")

    def test_optional_api_preserves_existing_gate(self):
        events, _ = fixture()
        events[7]["text"] = "右折田まっすぐは" + "右折" * 54 + "しています。"
        default = validate(events, require_turn_coverage=True)
        strict = validate(events, require_turn_coverage=True, max_ai_turn_chars=96)
        self.assertEqual(default["gate"], "PASS")
        self.assertEqual(default["max_ai_turn_chars"], "NOT_REQUESTED")
        self.assertEqual(strict["gate"], "FAIL")

    def test_boundary_inclusive(self):
        events, _ = fixture()
        events[7]["text"] = "右折" * 48
        result = validate(events, max_ai_turn_chars=96)
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(next(x["characters"] for x in result["ai_turn_char_counts"] if x["event"] == 7), 96)

    def test_exact_script_first_two_are_exempt(self):
        events, _ = fixture()
        result = validate(events, max_ai_turn_chars=25)
        self.assertEqual(result["gate"], "FAIL")
        violations = [x for x in result["violations"] if x["reason"] == "ai_turn_exceeds_char_budget_proxy"]
        self.assertTrue(violations)
        self.assertTrue(all(v["event"] > 3 for v in violations))

    def test_invalid_limits_fail_closed(self):
        events, _ = fixture()
        for value in [True, 0, -4, "96", 3.2]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate(events, max_ai_turn_chars=value)


if __name__ == "__main__":
    unittest.main()
