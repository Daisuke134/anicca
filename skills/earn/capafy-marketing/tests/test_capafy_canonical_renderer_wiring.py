#!/usr/bin/env python3
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "capafy-ig-marketing-daily.sh"


class ApprovedHyperFramesWiringTest(unittest.TestCase):
    def test_step3_uses_approved_hyperframes_and_andrew_voice(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("$LIFE_MANAGER_REPO/skills/video/hyperframes/capafy-o13-review/", source)
        self.assertIn("hyperframes@0.8.8 render", source)
        self.assertIn("edge-tts --voice en-US-AndrewNeural", source)
        self.assertIn("four listing-specific 1080x1920 scenes", source)
        self.assertIn("zero scene-boundary crossings", source)
        self.assertIn("repo-owned test fixture or immutable live output receipt", source)
        self.assertIn("inspect full-resolution frames from all four scenes", source)
        self.assertNotIn("say -v Samantha", source)
        self.assertNotIn("skills/video/canonical-renderer/render.py", source)

    def test_runtime_has_no_repo_external_faceless_renderer(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("~/.claude/skills/faceless-money-factory", source)
        self.assertNotIn("~/.agents/skills/faceless-money-factory", source)

    def test_live_pass_selects_once_and_requires_new_native_reel_before_success(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("STEP1 SELECTED (deterministic caller; do not call selector again)", source)
        self.assertIn("evidence-ready listing selection failed", source)
        self.assertIn("live pass produced no verified native Reel", source)
        self.assertIn("--commit-agent-id", source)
        self.assertLess(source.index("VERIFIED_POST="), source.index("--commit-agent-id"))


if __name__ == "__main__":
    unittest.main()
