#!/usr/bin/env python3
"""Synthetic tests: no audience, voice, or provider model calls."""
import json
import tempfile
import unittest
from pathlib import Path
from audit_response_repetition import audit, canonical, similarity


class RepetitionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, answers):
        path = self.root / name
        path.write_text("".join(json.dumps({"task_id": str(i), "response": a}, ensure_ascii=False) + "\n"
                                for i, a in enumerate(answers)), encoding="utf-8")
        return path

    def test_unicode_punctuation_normalization(self):
        self.assertEqual(canonical("ＡＩ！ 田中、です。"), canonical("AI田中です"))

    def test_exact_duplicate_with_punctuation_is_flagged(self):
        current = self.file("c.jsonl", ["救急車が校長室で卒業式を始めました！"])
        old = self.file("h.jsonl", ["救急車が校長室で卒業式を始めました。"])
        result = audit(current, [old])
        self.assertEqual(result["historical_flags"], 1)
        self.assertEqual(result["review_flags"][0]["similarity"], 1.0)

    def test_within_run_duplicate(self):
        current = self.file("c.jsonl", ["救急車が校長室で卒業式を始めました。", "救急車が校長室で卒業式を始めました！"])
        self.assertEqual(audit(current, [])["within_run_flags"], 1)

    def test_different_short_texts_are_not_flagged(self):
        current = self.file("c.jsonl", ["押印が必要です"])
        old = self.file("h.jsonl", ["最終電車に遅れました"])
        self.assertEqual(audit(current, [old])["historical_flags"], 0)

    def test_shared_character_name_alone_not_exact_duplication(self):
        x = "右折田まっすぐは切符を買いに駅へ向かいました。"
        y = "右折田まっすぐは図書館で消しゴムを借りました。"
        self.assertLess(similarity(x, y), 0.70)

    def test_threshold_boundary(self):
        current = self.file("c.jsonl", ["同じ台詞"])
        old = self.file("h.jsonl", ["同じ台詞"])
        self.assertEqual(audit(current, [old], 1.0)["historical_flags"], 1)

    def test_no_false_proof_of_humor(self):
        current = self.file("c.jsonl", ["台詞です"])
        report = audit(current, [])
        self.assertEqual(report["humor_quality"], "NOT_MEASURED")
        self.assertEqual(report["semantic_originality"], "NOT_MEASURED")

    def test_invalid_threshold_rejected(self):
        current = self.file("c.jsonl", ["台詞です"])
        for value in (-0.01, 1.01, float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit(current, [], value)

    def test_history_cannot_be_current(self):
        current = self.file("c.jsonl", ["台詞です"])
        with self.assertRaises(ValueError):
            audit(current, [current])

    def test_empty_response_rejected(self):
        current = self.file("c.jsonl", [""])
        with self.assertRaises(ValueError):
            audit(current, [])

    def test_invalid_json_rejected(self):
        current = self.root / "bad.jsonl"
        current.write_text("{broken}\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            audit(current, [])


if __name__ == "__main__":
    unittest.main()
