from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]


class XRoleSeparationTests(unittest.TestCase):
    def test_tweeter_is_original_only_with_independent_state_and_queues(self) -> None:
        tweeter = (ROOT / "skills" / "x-tweeter" / "x-tweeter-cli.sh").read_text()
        repost = tomllib.loads((ROOT / "loops" / "x-repost" / "loop.toml").read_text())
        tweeter_loop = tomllib.loads((ROOT / "loops" / "x-tweeter" / "loop.toml").read_text())

        self.assertEqual(repost["env"]["X_REPOST_FORCE_KIND"], "quote")
        self.assertIn("X_REPOST_FORCE_KIND=original", tweeter)
        self.assertIn("X_REPOST_DISABLE_AFFILIATE=1", tweeter)
        self.assertIn("no-affiliate-proposal.json", tweeter)
        self.assertIn("no-affiliate-jobs.jsonl", tweeter)
        self.assertNotEqual(repost["state_dir"], tweeter_loop["state_dir"])


if __name__ == "__main__":
    unittest.main()
