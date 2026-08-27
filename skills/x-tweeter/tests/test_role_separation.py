from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]


class XRoleSeparationTests(unittest.TestCase):
    def test_tweeter_is_original_only_with_independent_state_and_queues(self) -> None:
        english_repost = (ROOT / "skills" / "x-repost" / "x-repost-en-cli.sh").read_text()
        tweeter = (ROOT / "skills" / "x-tweeter" / "x-tweeter-cli.sh").read_text()
        repost = tomllib.loads((ROOT / "loops" / "x-repost" / "loop.toml").read_text())
        tweeter_loop = tomllib.loads((ROOT / "loops" / "x-tweeter" / "loop.toml").read_text())

        self.assertEqual(repost["env"]["X_REPOST_FORCE_KIND"], "quote")
        self.assertEqual(repost["env"]["X_REPOST_FORCE_LANGUAGE"], "en")
        self.assertEqual(repost["env"]["X_REPOST_DISABLE_AFFILIATE"], "1")
        self.assertEqual(repost["state_dir"], "~/loops/x-repost-en")
        self.assertEqual(repost["jobs"]["pass"]["program"],
                         "skills/x-repost/x-repost-en-cli.sh")
        self.assertIn("no-affiliate-proposal.json", english_repost)
        self.assertIn("no-affiliate-jobs.jsonl", english_repost)
        self.assertEqual(repost["jobs"]["pass"]["calendars"], [
            {"minute": 0}, {"minute": 30},
        ])
        self.assertIn("X_REPOST_FORCE_KIND=original", tweeter)
        self.assertIn("X_REPOST_DISABLE_AFFILIATE=1", tweeter)
        self.assertIn("no-affiliate-proposal.json", tweeter)
        self.assertIn("no-affiliate-jobs.jsonl", tweeter)
        self.assertNotEqual(repost["state_dir"], tweeter_loop["state_dir"])

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

    def test_public_source_detail_can_replace_an_exhausted_firsthand_seed(self) -> None:
        source = (ROOT / "skills" / "x-repost" / "x-repost-cli.sh").read_text()

        self.assertNotIn("合う種が無ければ selected=false", source)
        self.assertNotIn("一次情報の種が無いため投稿を見送り", source)
        self.assertNotIn('finish 0 "unique firsthand seed contract failed"', source)
        self.assertIn("source固有のexact detail", source)
        self.assertIn("source evidence replaces firsthand seed", source)

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
