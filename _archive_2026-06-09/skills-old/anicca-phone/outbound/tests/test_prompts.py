"""Pure-text regression tests for bot.py's system prompts.

These deliberately avoid importing bot.py — it pulls heavy runtime deps
(pipecat, loguru, fastapi) that the CI lint job doesn't install. We
parse the source as text and simulate ``pick_system_instruction`` so the
regression checks run anywhere a stdlib Python sits.

Run:
    python3 -m unittest skills.anicca-phone.outbound.tests.test_prompts -v
or directly:
    python3 skills/anicca-phone/outbound/tests/test_prompts.py
"""
from __future__ import annotations

import os
import re
import unittest


BOT_PY = os.path.join(os.path.dirname(__file__), "..", "bot.py")


def _extract(name: str, src: str) -> str:
    m = re.search(rf'{name} = """\\?\n?(.*?)"""', src, re.S)
    if not m:
        raise AssertionError(f"could not locate {name} block in bot.py")
    return m.group(1)


def _pick(mode: str, ctx: str, name: str, src: str) -> str:
    """Reproduce pick_system_instruction in pure text."""
    block = "ANICCA_LATENESS_SYSTEM_INSTRUCTION" if mode == "lateness" else "ANICCA_WAKEUP_SYSTEM_INSTRUCTION"
    base = _extract(block, src)
    base = base.replace("{name}", name or "friend")
    if mode == "lateness":
        base = base.replace(
            "{ctx}",
            ctx or "(no specific context — operator may be running late from any location)",
        )
    return base


class PromptSubstitutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(BOT_PY, encoding="utf-8") as f:
            cls.src = f.read()

    def test_name_placeholder_is_substituted_in_wakeup(self) -> None:
        rendered = _pick("wakeup", "", "Alice", self.src)
        self.assertNotIn("{name}", rendered, "literal {name} would be spoken to caller")
        self.assertIn("Alice", rendered)

    def test_name_placeholder_is_substituted_in_lateness(self) -> None:
        rendered = _pick("lateness", "going to 中野駅", "Alice", self.src)
        self.assertNotIn("{name}", rendered)
        self.assertNotIn("{ctx}", rendered)
        self.assertIn("Alice", rendered)
        self.assertIn("中野駅", rendered)

    def test_empty_name_falls_back_to_friend(self) -> None:
        rendered = _pick("wakeup", "", "", self.src)
        self.assertNotIn("{name}", rendered)
        self.assertIn("friend", rendered)


    def test_lateness_prompt_preserves_hard_rule_against_home_assumption(self) -> None:
        rendered = _pick("lateness", "", "User", self.src)
        self.assertIn("家を出ろ", rendered)
        self.assertIn("HARD RULE", rendered)

    def test_lateness_prompt_preserves_route_trust_block(self) -> None:
        rendered = _pick("lateness", "", "User", self.src)
        self.assertIn("推奨ルート", rendered)
        self.assertIn("get_directions", rendered)

    def test_prompts_stay_below_size_budget(self) -> None:
        # Hard cap so future authors don't silently re-bloat the prompts.
        # Current sizes (2026-06-01): wakeup 639 chars, lateness 1369 chars.
        wakeup = _pick("wakeup", "", "Caller", self.src)
        lateness = _pick("lateness", "", "Caller", self.src)
        self.assertLess(
            len(wakeup), 1200,
            f"wakeup prompt grew to {len(wakeup)} chars — Gemini Live first-token latency will regress",
        )
        self.assertLess(
            len(lateness), 2000,
            f"lateness prompt grew to {len(lateness)} chars — Gemini Live first-token latency will regress",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
