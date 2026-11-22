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


if __name__ == "__main__":
    unittest.main()
