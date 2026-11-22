#!/usr/bin/env python3
"""Regressions: repetitive questioning and incomplete strict submissions."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_run import score


class QuestionGateTests(unittest.TestCase):
    def test_zero_questions_allows_plain_stage_action(self):
        self.assertEqual(score({"kind": "adlib", "max_questions": 0}, "丸山が窓だけ運びました。"), [])

    def test_fullwidth_and_ascii_question_marks_fail(self):
        for text in ("住所はどこですか？", "住所はどこですか?", "どこ? 何階？"):
            with self.subTest(text=text):
                self.assertIn("exceeds_max_questions", score({"kind": "adlib", "max_questions": 0}, text))

    def test_one_question_limit(self):
        self.assertEqual(score({"kind": "adlib", "max_questions": 1}, "どこ？"), [])
        self.assertIn("exceeds_max_questions", score({"kind": "adlib", "max_questions": 1}, "どこ? 何階？"))

    def test_invalid_question_cap_fails_closed(self):
        for value in (-1, True, "0", 0.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    score({"kind": "adlib", "max_questions": value}, "こんにちは")

    def test_existing_tasks_without_cap_unchanged(self):
        self.assertEqual(score({"kind": "adlib"}, "どこ？何階？"), [])

    def test_strict_cli_rejects_missing_tasks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "tasks.jsonl").write_text('{"id":"one","kind":"generation"}\n{"id":"two","kind":"generation"}\n', encoding="utf-8")
            (p / "responses.jsonl").write_text(json.dumps({
                "run_id": "partial", "task_id": "one", "model": "example", "skill_version": "0.1",
                "skill_commit": "test", "response": "okay",
            }) + "\n", encoding="utf-8")
            args = [sys.executable, str(Path(__file__).with_name("validate_run.py")),
                    "--tasks", str(p / "tasks.jsonl"), "--responses", str(p / "responses.jsonl"),
                    "--output", str(p / "report.json")]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(args + ["--strict"], capture_output=True).returncode, 1)

    def test_strict_cli_rejects_zero_submissions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "tasks.jsonl").write_text('{"id":"one","kind":"generation"}\n', encoding="utf-8")
            (p / "responses.jsonl").write_text('', encoding="utf-8")
            args = [sys.executable, str(Path(__file__).with_name("validate_run.py")),
                    "--tasks", str(p / "tasks.jsonl"), "--responses", str(p / "responses.jsonl"),
                    "--output", str(p / "report.json"), "--strict"]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 1)


if __name__ == "__main__":
    unittest.main()
