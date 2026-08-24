from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]


class XRoleSeparationTests(unittest.TestCase):
    def test_repost_is_quote_only_and_tweeter_is_original_only(self) -> None:
        repost = tomllib.loads((
            ROOT / "loops" / "x-repost" / "loop.toml"
        ).read_text(encoding="utf-8"))
        tweeter = (
            ROOT / "skills" / "x-tweeter" / "x-tweeter-cli.sh"
        ).read_text(encoding="utf-8")

        self.assertEqual(repost["env"]["X_REPOST_FORCE_KIND"], "quote")
        self.assertEqual(repost["jobs"]["pass"]["calendars"], [
            {"minute": 0}, {"minute": 30},
        ])
        self.assertIn("X_REPOST_FORCE_KIND=original", tweeter)
        self.assertNotEqual(
            repost["state_dir"],
            tomllib.loads((ROOT / "loops" / "x-tweeter" / "loop.toml").read_text())["state_dir"],
        )


if __name__ == "__main__":
    unittest.main()
