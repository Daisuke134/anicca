import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_operator import (
    MercorOperatorError,
    create_operator_config,
    operator_state_root,
)


class MercorOperatorTests(unittest.TestCase):
    def test_operator_state_isolated_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.json"
            resume = root / "resume.pdf"
            profile.write_text('{"version":1}\n', encoding="utf-8")
            resume.write_bytes(b"pdf")
            config = create_operator_config(
                operator_id="operator-a",
                profile_path=profile,
                resume_path=resume,
                base_root=root / "state",
                locales=["ja", "en", "ja"],
                role_families=["AI", "data"],
                weekly_hours=40,
                exclusions=["employer-a"],
            )
            self.assertTrue(Path(config.state_root).is_dir())
            self.assertEqual(Path(config.state_root).stat().st_mode & 0o777, 0o700)
            operator_file = Path(config.state_root) / "operator.json"
            self.assertEqual(operator_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(operator_file.read_text())["locales"], ["en", "ja"])
            stored = json.loads(operator_file.read_text())
            self.assertNotIn("facts", stored)
            self.assertNotIn("password", stored)
            self.assertNotIn("token", stored)

    def test_invalid_id_and_weekly_hours_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(MercorOperatorError):
                operator_state_root("../escape", base_root=root)
            profile = root / "profile.json"
            resume = root / "resume.pdf"
            profile.write_text("profile", encoding="utf-8")
            resume.write_bytes(b"pdf")
            with self.assertRaises(MercorOperatorError):
                create_operator_config(
                    operator_id="operator-a",
                    profile_path=profile,
                    resume_path=resume,
                    base_root=root / "state",
                    locales=["en"],
                    role_families=["AI"],
                    weekly_hours=81,
                )


if __name__ == "__main__":
    unittest.main()
