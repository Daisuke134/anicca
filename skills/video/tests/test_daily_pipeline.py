#!/usr/bin/env python3
"""9c: the daily loop must pick a genuinely new creative and speak it as narration.

The old runtime read one hardcoded call recording, so every day sounded the same and the video could
only ever be about that one call. These tests pin the two decisions the loop actually makes: which
creative runs today, and what the voice says.
"""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "daily-lm-video" / "daily_pipeline.py"
SPEC = importlib.util.spec_from_file_location("daily_pipeline", MODULE_PATH)
daily_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(daily_pipeline)


BANK = [
    {
        "id": "A01",
        "pain": "アラーム3回スヌーズ", "moment": "電話が鳴る", "punchline": "人に起こされた朝",
        "pain_en": "you snooze three times and lose the morning",
        "moment_en": "a real call tells you to leave at nine thirty",
        "punchline_en": "a morning somebody woke you up for",
    },
    {
        "id": "A02",
        "pain": "移動時間を手入力", "moment": "travel time が勝手に埋まる", "punchline": "気づいたら埋まってる",
        "pain_en": "you still work out your own travel time",
        "moment_en": "the travel block fills itself in the moment you save the event",
        "punchline_en": "it is already there before you look",
    },
    {
        "id": "A03",
        "pain": "頭の RAM に常駐", "moment": "T-10 / T-5 の2段階 call", "punchline": "時計を見る仕事が消える",
        "pain_en": "a clock runs in your head all day",
        "moment_en": "it calls at ten minutes out, then five, until you pick up",
        "punchline_en": "the job of watching the clock is gone",
    },
]


class NextCreativeTests(unittest.TestCase):
    def test_an_empty_ledger_starts_at_the_first_creative(self):
        self.assertEqual(daily_pipeline.next_creative(BANK, [])["id"], "A01")

    def test_the_loop_advances_instead_of_repeating_yesterday(self):
        self.assertEqual(daily_pipeline.next_creative(BANK, [{"creative_id": "A01"}])["id"], "A02")
        self.assertEqual(
            daily_pipeline.next_creative(BANK, [{"creative_id": "A01"}, {"creative_id": "A02"}])["id"],
            "A03",
        )

    def test_a_full_cycle_wraps_back_to_the_start(self):
        used = [{"creative_id": row["id"]} for row in BANK]
        self.assertEqual(daily_pipeline.next_creative(BANK, used)["id"], "A01")

    def test_only_the_most_recent_entry_decides_the_next_one(self):
        # Ledger rows arrive newest-last; a stale A03 far back must not drag the rotation backwards.
        used = [{"creative_id": "A03"}, {"creative_id": "A01"}]
        self.assertEqual(daily_pipeline.next_creative(BANK, used)["id"], "A02")

    def test_a_ledger_naming_an_unknown_creative_restarts_rather_than_crashing(self):
        self.assertEqual(daily_pipeline.next_creative(BANK, [{"creative_id": "GONE"}])["id"], "A01")

    def test_an_empty_bank_has_nothing_to_run(self):
        self.assertIsNone(daily_pipeline.next_creative([], []))


class NarrationTests(unittest.TestCase):
    def test_english_narration_follows_problem_then_solution_then_payoff(self):
        script = daily_pipeline.narration_script(BANK[0], "en")
        self.assertIn("Life Manager", script)
        # The narration is prose for a voice, not the raw bank fields read out.
        self.assertNotIn("pain:", script)
        self.assertNotIn("punchline:", script)
        self.assertGreater(len(script.split()), 25)

    def test_japanese_narration_is_japanese_and_carries_the_same_beats(self):
        script = daily_pipeline.narration_script(BANK[0], "ja")
        self.assertIn("Life Manager", script)
        self.assertIn("アラーム3回スヌーズ", script)

    def test_each_creative_produces_a_different_narration(self):
        scripts = {daily_pipeline.narration_script(row, "en") for row in BANK}
        self.assertEqual(len(scripts), len(BANK))

    def test_an_unknown_language_is_refused_rather_than_silently_english(self):
        with self.assertRaises(ValueError):
            daily_pipeline.narration_script(BANK[0], "fr")

    def test_a_creative_missing_a_beat_is_refused(self):
        with self.assertRaises(ValueError):
            daily_pipeline.narration_script({"id": "X", "pain": "only pain"}, "en")


class RenderCommandTests(unittest.TestCase):
    def test_the_render_command_passes_our_script_so_no_llm_is_involved(self):
        argv = daily_pipeline.render_argv(
            script="A narration.",
            materials=[Path("/tmp/a.mp4"), Path("/tmp/b.mp4")],
            task_id="11111111-2222-3333-4444-555555555555",
            voice="en-US-AndrewNeural",
        )
        self.assertIn("--video-script", argv)
        self.assertIn("A narration.", argv)
        # Local materials only: the loop must not depend on a stock API key.
        self.assertIn("--video-source", argv)
        self.assertEqual(argv[argv.index("--video-source") + 1], "local")
        self.assertEqual(argv[argv.index("--video-materials") + 1], "/tmp/a.mp4,/tmp/b.mp4")
        self.assertEqual(argv[argv.index("--video-aspect") + 1], "9:16")
        self.assertEqual(argv[argv.index("--voice-name") + 1], "en-US-AndrewNeural")

    def test_a_render_without_materials_is_refused(self):
        with self.assertRaises(ValueError):
            daily_pipeline.render_argv(
                script="A narration.", materials=[], task_id="t", voice="en-US-AndrewNeural",
            )


if __name__ == "__main__":
    unittest.main()
