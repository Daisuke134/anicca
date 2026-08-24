import json
import os
import tempfile
import unittest
from pathlib import Path

from job_search_loop.config import ConfigError, load_settings, validate_profile


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.profile = self.root / "config" / "profile.json"
        self.strategy = self.root / "strategy.json"
        self.strategy.write_text(
            json.dumps(
                {
                    "version": 1,
                    "daily_target": 2,
                    "auto_apply_threshold": 75,
                    "compensation_floor_jpy": 7_000_000,
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _valid_profile(self):
        return {
            "version": 1,
            "candidate": {"name": "Daisuke Narita"},
            "facts": [
                {
                    "id": "muit_role_2025",
                    "claim": "MUIT, 2025-04–present",
                    "evidence": "user_statement",
                }
            ],
        }

    def test_missing_private_profile_fails_closed(self):
        with self.assertRaisesRegex(ConfigError, "profile"):
            load_settings(
                profile_path=self.profile,
                strategy_path=self.strategy,
                state_dir=self.root / "state",
                materials_dir=self.root / "materials",
            )

    def test_defaults_and_private_permissions(self):
        self.profile.parent.mkdir(parents=True)
        self.profile.write_text(json.dumps(self._valid_profile()), encoding="utf-8")
        os.chmod(self.profile, 0o600)
        settings = load_settings(
            profile_path=self.profile,
            strategy_path=self.strategy,
            state_dir=self.root / "state",
            materials_dir=self.root / "materials",
        )
        self.assertEqual(settings.daily_target, 2)
        self.assertEqual(settings.auto_apply_threshold, 75)
        self.assertEqual(settings.compensation_floor_jpy, 7_000_000)
        self.assertEqual(settings.state_dir.stat().st_mode & 0o777, 0o700)
        self.assertEqual(settings.materials_dir.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.profile.stat().st_mode & 0o777, 0o600)

    def test_incomplete_fact_is_rejected(self):
        value = self._valid_profile()
        del value["facts"][0]["evidence"]
        with self.assertRaisesRegex(ConfigError, "evidence"):
            validate_profile(value)

    def test_committed_strategy_contains_no_private_fields(self):
        strategy_path = (
            Path(__file__).parents[1] / "config" / "strategy.default.json"
        )
        text = strategy_path.read_text(encoding="utf-8").lower()
        for forbidden in ("email", "phone", "address", "token", "cookie"):
            self.assertNotIn(forbidden, text)

    def test_committed_strategy_includes_technical_business_roles(self):
        strategy_path = (
            Path(__file__).parents[1] / "config" / "strategy.default.json"
        )
        value = json.loads(strategy_path.read_text(encoding="utf-8"))
        expected = {
            "ai_product_management",
            "technical_program_management",
            "ai_business_development",
            "ai_partnerships",
            "technical_account_management",
            "ai_customer_success",
            "ai_sales_engineering",
        }
        self.assertTrue(expected <= set(value["role_families"]))


if __name__ == "__main__":
    unittest.main()
