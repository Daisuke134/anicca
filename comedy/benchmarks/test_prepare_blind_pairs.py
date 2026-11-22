#!/usr/bin/env python3
"""Offline regression tests for counterbalanced review preparation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_blind_pairs import prepare


def example(n=8):
    tasks = []
    responses = []
    for i in range(n):
        task_id = f"original-{i:02d}"
        tasks.append({
            "id": task_id, "category": "oogiri", "kind": "generation",
            "prompt": f"架空の店長が第{i}回の朝礼で何をした？",
            "max_chars": 90, "max_questions": 0,
            "rights": "original_internal_draft",
            "set_type": "original_development_not_fixed_benchmark",
        })
        for idx in (1, 2):
            responses.append({
                "task_id": task_id, "sample_index": idx,
                "response": f"紙の店長が{idx}番の棚を表彰して帰りました。",
                "model": "hidden-model",
                "skill_blob_sha": "a" * 40,
                "run_id": f"private-run-{idx}",
            })
    return tasks, responses


class CounterbalanceTests(unittest.TestCase):
    def test_balanced_eight_tasks(self):
        tasks, rows = example()
        report = prepare(tasks, rows, "research-seed")
        self.assertEqual(report["pairs"], 8)
        self.assertEqual(report["candidate_count"], 16)
        self.assertEqual(report["position_balance"]["v1"]["sample_1"], 4)
        self.assertEqual(report["position_balance"]["v1"]["sample_2"], 4)

    def test_odd_task_count_diff_at_most_one(self):
        tasks, rows = example(7)
        report = prepare(tasks, rows, "research-seed")
        counts = report["position_balance"]["v1"]
        self.assertLessEqual(abs(counts["sample_1"] - counts["sample_2"]), 1)

    def test_variants_reverse_each_pair(self):
        tasks, rows = example(4)
        report = prepare(tasks, rows, "a")
        for one, two in zip(report["variants"]["v1"], report["variants"]["v2"]):
            self.assertEqual(one["A"], two["B"])
            self.assertEqual(one["B"], two["A"])

    def test_order_and_result_are_reproducible(self):
        tasks, rows = example()
        one = prepare(tasks, rows, "a")
        two = prepare(list(reversed(tasks)), list(reversed(rows)), "a")
        self.assertEqual(one, two)

    def test_packet_hides_model_and_run_metadata(self):
        tasks, rows = example(2)
        report = prepare(tasks, rows, "s")
        for item in report["variants"]["v1"]:
            self.assertTrue({"pair_id", "prompt", "A", "B"}.issubset(item))
            self.assertFalse({"model", "model_version", "run_id", "skill_blob_sha"} & set(item))

    def test_missing_candidate_rejected(self):
        tasks, rows = example(2)
        with self.assertRaisesRegex(ValueError, "exactly two"):
            prepare(tasks, rows[:-1], "s")

    def test_duplicate_candidate_rejected(self):
        tasks, rows = example(1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare(tasks, rows + [rows[0]], "s")

    def test_failed_hard_gate_rejected(self):
        tasks, rows = example(1)
        rows[0]["response"] = "?" * 91
        with self.assertRaisesRegex(ValueError, "hard gate FAIL"):
            prepare(tasks, rows, "s")

    def test_unequal_skill_sha_rejected(self):
        tasks, rows = example(1)
        rows[1]["skill_blob_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "unequal Skill"):
            prepare(tasks, rows, "s")

    def test_unlicensed_task_rejected(self):
        tasks, rows = example(1)
        tasks[0]["rights"] = "unknown"
        with self.assertRaisesRegex(ValueError, "rights-cleared"):
            prepare(tasks, rows, "s")

    def test_no_human_score_claimed(self):
        tasks, rows = example(2)
        report = prepare(tasks, rows, "s")
        self.assertEqual(report["human_judgments"], 0)
        self.assertEqual(report["review_status"], "NOT_MEASURED")
        self.assertFalse(report["publish_enabled"])


if __name__ == "__main__":
    unittest.main()
