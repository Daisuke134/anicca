#!/usr/bin/env python3
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "capafy-ig-marketing-daily.sh"


class CanonicalRendererWiringTest(unittest.TestCase):
    def test_step3_uses_repo_owned_canonical_renderer(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("$LIFE_MANAGER_REPO/skills/video/canonical-renderer/render.py", source)
        self.assertIn("--hook", source)
        self.assertIn("--proof", source)
        self.assertIn("--cta", source)
        self.assertIn("--audio", source)
        self.assertIn("--output", source)
        self.assertIn("say -v Samantha -r 185 -f", source)
        self.assertIn("reel.manifest.json", source)
        self.assertIn("quality_gate=pass", source)
        self.assertIn("video_encode_passes=1", source)

    def test_runtime_has_no_repo_external_faceless_renderer(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("~/.claude/skills/faceless-money-factory", source)
        self.assertNotIn("~/.agents/skills/faceless-money-factory", source)


if __name__ == "__main__":
    unittest.main()
