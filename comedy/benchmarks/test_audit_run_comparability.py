#!/usr/bin/env python3
"""Synthetic comparison eligibility regressions; no provider calls or humor scoring."""
import unittest
from copy import deepcopy

from audit_run_comparability import audit

SKILL = "a" * 40
TASKS = [{"id": "new-g1"}, {"id": "new-s1"}]


def rows(model, source="independent_provider_api"):
    result = []
    for task in TASKS:
        for candidate in ("A", "B"):
            result.append({
                "model": model, "model_version": model + "-2026-11",
                "task_id": task["id"], "candidate": candidate,
                "response": "架空の回答です。",
                "invocation_source": source,
                "provider_receipt": "fixture-receipt-" + model,
                "skill_blob_sha": SKILL,
                "modality": "text", "temperature": "0.7", "effort": "medium",
                "task_origin": "NEW_ORIGINAL_INTERNAL_DEV", "fixed_benchmark": False,
                "publish": False,
            })
    return result


class ComparableRunTests(unittest.TestCase):
    def test_single_chat_not_comparable(self):
        out = audit(TASKS, rows("ChatGPT", "single_chat_no_independent_provider_call"))
        self.assertEqual(out["comparison_eligibility"], "NOT_COMPARABLE")
        self.assertIn("FEWER_THAN_TWO_EXECUTED_MODELS", out["reasons"])

    def test_synthetic_two_model_claims_are_only_conditional(self):
        out = audit(TASKS, rows("A") + rows("B"))
        self.assertEqual(out["comparison_eligibility"],
                         "CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED")
        self.assertFalse(out["actual_provider_receipts_verified"])
        self.assertEqual(out["funniness"], "NOT_MEASURED")

    def test_missing_provider_receipt_rejected(self):
        sample = rows("A") + rows("B")
        sample[-1]["provider_receipt"] = None
        self.assertEqual(audit(TASKS, sample)["comparison_eligibility"], "NOT_COMPARABLE")

    def test_unknown_product_build_rejected(self):
        sample = rows("A") + rows("B")
        for record in sample:
            record["model_version"] = "GPT-6_PRODUCT_LABEL_EXACT_BUILD_UNKNOWN"
        self.assertIn("UNKNOWN_MODEL_BUILD", audit(TASKS, sample)["models"][0]["issues"])

    def test_mismatched_skill_rejected(self):
        sample = rows("A") + rows("B")
        for record in sample[4:]:
            record["skill_blob_sha"] = "b" * 40
        self.assertIn("SKILL_SHA_MISMATCH", audit(TASKS, sample)["reasons"])

    def test_unbalanced_task_candidate_rejected(self):
        sample = rows("A") + rows("B")
        sample.pop()
        self.assertIn("UNBALANCED_TASK_CANDIDATE_COVERAGE",
                      audit(TASKS, sample)["reasons"])

    def test_settings_mismatch_rejected(self):
        sample = rows("A") + rows("B")
        for record in sample[4:]:
            record["temperature"] = "0.2"
        self.assertIn("INFERENCE_SETTINGS_MISMATCH", audit(TASKS, sample)["reasons"])

    def test_duplicate_candidate_rejected(self):
        sample = rows("A") + rows("B")
        sample.append(deepcopy(sample[0]))
        self.assertIn("DUPLICATE_TASK_CANDIDATE", audit(TASKS, sample)["models"][0]["issues"])

    def test_missing_task_rejected(self):
        sample = rows("A") + rows("B")
        sample = [r for r in sample if not (r["model"] == "B" and r["task_id"] == "new-s1")]
        self.assertIn("MISSING_TASKS", audit(TASKS, sample)["models"][1]["issues"])

    def test_publication_field_rejected(self):
        sample = rows("A") + rows("B")
        sample[0]["publish"] = True
        self.assertIn("PUBLICATION_MUST_BE_OFF", audit(TASKS, sample)["models"][0]["issues"])

    def test_modality_mismatch_rejected(self):
        sample = rows("A") + rows("B")
        for record in sample[4:]:
            record["modality"] = "voice"
        self.assertIn("MODALITY_MISMATCH", audit(TASKS, sample)["reasons"])

    def test_empty_taskset_fails(self):
        with self.assertRaises(ValueError):
            audit([], rows("A"))


    def test_symmetric_missing_candidate_per_task_is_rejected(self):
        # Both claimed models omit the same candidate on the same task.
        sample = [r for r in rows("A") + rows("B")
                  if not (r["task_id"] == "new-s1" and r["candidate"] == "B")]
        out = audit(TASKS, sample)
        self.assertEqual(out["comparison_eligibility"], "NOT_COMPARABLE")
        self.assertIn("LESS_THAN_TWO_CANDIDATES_PER_TASK", out["models"][0]["issues"])
        self.assertIn("UNEQUAL_CANDIDATES_PER_TASK", out["models"][0]["issues"])

    def test_single_candidate_for_every_task_is_rejected(self):
        sample = [r for r in rows("A") + rows("B") if r["candidate"] == "A"]
        out = audit(TASKS, sample)
        self.assertEqual(out["comparison_eligibility"], "NOT_COMPARABLE")
        self.assertIn("LESS_THAN_TWO_CANDIDATES_PER_TASK", out["models"][0]["issues"])

    def test_whitespace_non_silence_response_is_rejected(self):
        sample = rows("A") + rows("B")
        sample[0]["response"] = " 　"
        out = audit(TASKS, sample)
        self.assertIn("EMPTY_NON_SILENCE_RESPONSE", out["models"][0]["issues"])

    def test_empty_silence_response_is_valid_for_claimed_conditions(self):
        tasks = deepcopy(TASKS)
        tasks[1]["kind"] = "silence"
        sample = rows("A") + rows("B")
        for r in sample:
            if r["task_id"] == "new-s1":
                r["response"] = ""
        out = audit(tasks, sample)
        self.assertEqual(out["comparison_eligibility"],
                         "CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED")

    def test_nonempty_silence_response_is_rejected(self):
        tasks = deepcopy(TASKS)
        tasks[1]["kind"] = "silence"
        sample = rows("A") + rows("B")
        out = audit(tasks, sample)
        self.assertIn("UNEXPECTED_RESPONSE_TO_SILENCE", out["models"][0]["issues"])

    def test_missing_nonstring_response_still_rejected(self):
        sample = rows("A") + rows("B")
        sample[0]["response"] = None
        out = audit(TASKS, sample)
        self.assertIn("MISSING_RESPONSE_TEXT", out["models"][0]["issues"])


if __name__ == "__main__":
    unittest.main()
