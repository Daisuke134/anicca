#!/usr/bin/env python3
"""Static contract checks only: no claims about speech recognition or stage success."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, BENCHMARKS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script_checker = load_module("injury_2min_checker", "check_injury_2min.py")
dialogue_checker = load_module("stage_dialogue_checker", "validate_stage_dialogue.py")


class StageVoiceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "sagi-injury-help-2min-live.md").read_text(encoding="utf-8")
        cls.turns = script_checker.extract_dialogues(cls.script)
        cls.ai_lines = [text for speaker, text in cls.turns if speaker == "チャッピー"]

    def test_stage_first_and_second_are_exact(self):
        self.assertEqual(self.turns[0][0], "ダイス")
        self.assertEqual(self.ai_lines[:2], [script_checker.FIRST, script_checker.SECOND])

    def test_dialogue_validator_uses_selected_script_exactly(self):
        self.assertEqual(dialogue_checker.OPENING, self.ai_lines[0])
        self.assertEqual(dialogue_checker.SECOND, self.ai_lines[1])

    def test_voice_prompt_contains_both_exact_script_lines(self):
        content = (ROOT / "prompts" / "INJURY-STAGE-LOCK-2MIN.md").read_text(encoding="utf-8")
        self.assertIn(self.ai_lines[0], content)
        self.assertIn(self.ai_lines[1], content)

    def test_operator_and_skill_instructions_agree_on_second_line(self):
        for filename in ("AGENTS.md", "../skills/comedy-agent/SKILL.md"):
            with self.subTest(filename=filename):
                content = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn(self.ai_lines[1], content)


    def test_historical_quote_variant_fails_exact_stage_gate(self):
        previous = self.ai_lines[1].replace(
            "「急性ひざの里帰りスペシャル」", "『急性ひざの里帰りスペシャル』"
        )
        self.assertNotEqual(previous, self.ai_lines[1])
        events = [
            {"speaker": "dais", "text": "痛い！", "cue": "start"},
            {"speaker": "ai", "text": self.ai_lines[0]},
            {"speaker": "dais", "text": "救急！痛い！"},
            {"speaker": "ai", "text": previous},
            {"speaker": "dais", "text": "終演", "cue": "end"},
        ]
        reasons = [item["reason"] for item in dialogue_checker.validate(events)["violations"]]
        self.assertIn("second_not_exact", reasons)


if __name__ == "__main__":
    unittest.main()
