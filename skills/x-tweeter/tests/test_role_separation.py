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

    def test_repost_enforces_persona_points_and_rolling_70_30_language_mix(self) -> None:
        source = (ROOT / "skills" / "x-repost" / "x-repost-cli.sh").read_text()
        for key in (
            "does_not_disparage", "includes_positive_note", "adds_unique_firsthand_detail",
            "avoids_excessive_self_focus", "leads_to_action",
        ):
            self.assertIn(key, source)
        self.assertIn('all(d.get("five_points", {}).get(key) is True', source)
        self.assertIn('${X_REPOST_FORCE_LANGUAGE:-}', source)
        self.assertIn('len(rows) % 10 < 7', source)
        self.assertIn('rolling EN 7 / JA 3', source)
        self.assertIn('post_contract.py" --language "$TARGET_LANGUAGE"', source)

    def test_affiliate_success_recovery_precedes_new_claim(self) -> None:
        source = (ROOT / "skills" / "x-repost" / "x-repost-cli.sh").read_text()
        recovery = source.index("affiliate-success-recovery.json")
        claim = source.index("--claim-next-job")
        self.assertLess(recovery, claim)
        self.assertIn('affiliate-job-effect.json', source)
        self.assertIn('recovered prior Affiliate success receipt', source)

    def test_launchd_model_call_cannot_wait_on_inherited_stdin(self) -> None:
        source = (ROOT / "skills" / "x-repost" / "x-repost-cli.sh").read_text()
        self.assertIn('"$(cat "$prompt_file")" </dev/null', source)


if __name__ == "__main__":
    unittest.main()
