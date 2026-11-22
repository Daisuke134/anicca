#!/usr/bin/env python3
"""Offline unit tests for Comedy benchmark validation. Run from repo root."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("validate_run.py")
spec = importlib.util.spec_from_file_location("comedy_validator", MODULE_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ComedyBenchmarkTests(unittest.TestCase):
    def test_canonical_opening_passes(self):
        task = {
            "kind": "opening",
            "expected_prefix": "はい、救急指令センターです。",
            "forbidden": ["深呼吸", "吸って", "吐いて"],
        }
        self.assertEqual(
            validator.score(task, "はい、救急指令センターです。火事ですか、救急ですか？"),
            [],
        )

    def test_breathing_deviation_is_failed(self):
        task = {
            "kind": "opening",
            "expected_prefix": "はい、救急指令センターです。",
            "forbidden": ["深呼吸", "吸って", "吐いて"],
        }
        issues = validator.score(task, "落ち着いて。吸って、吐いて。")
        self.assertIn("opening_or_script_prefix_mismatch", issues)
        self.assertIn("forbidden_phrase:吸って", issues)
        self.assertIn("forbidden_phrase:吐いて", issues)

    def test_exact_line_rejects_appended_triage(self):
        line = "はい、救急指令センターです。火事ですか、救急ですか？"
        task = {"kind": "opening", "expected_prefix": line, "expected_exact": line}
        response = line + "住所を教えてください。"
        self.assertEqual(validator.score(task, response), ["script_exact_response_mismatch"])

    def test_exact_second_line_rejects_truncation(self):
        line = "救急ですね。声で分かりました。右ひざがご実家に帰られています。"
        task = {"kind": "continuation", "expected_exact": line}
        self.assertIn("script_exact_response_mismatch", validator.score(task, line[:-1]))

    def test_exact_line_accepts_identical_full_turn(self):
        line = "救急ですね。声で分かりました。右ひざがご実家に帰られています。"
        self.assertEqual(validator.score({"kind": "continuation", "expected_exact": line}, line), [])

    def test_exact_contract_requires_nonempty_string(self):
        for value in ("", True, 0, []):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validator.score({"kind": "opening", "expected_exact": value}, "はい")

    def test_prefix_only_contract_preserved(self):
        line = "はい、救急指令センターです。火事ですか、救急ですか？"
        self.assertEqual(validator.score({"kind": "opening", "expected_prefix": line},
                                         line + "（ここから余分な台詞）"), [])

    def test_spectator_requires_silence(self):
        self.assertEqual(validator.score({"kind": "silence"}, ""), [])
        self.assertEqual(validator.score({"kind": "silence"}, "  "), [])
        self.assertEqual(validator.score({"kind": "silence"}, "もしもし"), ["expected_silence"])

    def test_improvisation_anchor(self):
        task = {"kind": "adlib", "any_of": ["会田", "面会", "おもち34号"]}
        self.assertEqual(validator.score(task, "会田アイタロウが面会を手配しました。"), [])
        self.assertIn("missing_required_world_anchor", validator.score(task, "なんだろう。"))

    def test_jsonl_and_run_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            tasks = folder / "tasks.jsonl"
            responses = folder / "responses.jsonl"
            tasks.write_text(
                json.dumps({"id": "a", "kind": "opening", "expected_prefix": "はい"}) + "\n",
                encoding="utf-8",
            )
            responses.write_text(
                json.dumps(
                    {
                        "run_id": "test", "task_id": "a", "model": "example",
                        "skill_version": "0.1", "skill_commit": "fake-test-sha",
                        "response": "はい、救急指令センターです。",
                    }, ensure_ascii=False
                ) + "\n",
                encoding="utf-8",
            )
            report = validator.run(tasks, responses)
            self.assertEqual(report["run_summary"][0]["passed"], 1)
            self.assertEqual(report["items"][0]["funniness"], "NOT_MEASURED")


    def test_max_chars_exact_limit_passes(self):
        self.assertEqual(validator.score({"kind": "generation", "max_chars": 80}, "あ" * 80), [])

    def test_max_chars_over_limit_fails(self):
        self.assertEqual(
            validator.score({"kind": "generation", "max_chars": 80}, "あ" * 81),
            ["exceeds_max_chars"],
        )

    def test_max_chars_invalid_fails_closed(self):
        for value in (0, True, "80"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validator.score({"kind": "generation", "max_chars": value}, "あ")

    def test_existing_generation_without_limit_unchanged(self):
        self.assertEqual(validator.score({"kind": "generation"}, "あ" * 81), [])


if __name__ == "__main__":
    unittest.main()
