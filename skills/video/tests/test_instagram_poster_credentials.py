#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
POSTER_PATH = ROOT / "skills/earn/marketing-engine/poster.py"
SPEC = importlib.util.spec_from_file_location("shared_instagram_poster", POSTER_PATH)
poster = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(poster)


class InstagramPosterCredentialTests(unittest.TestCase):
    def test_accepts_existing_account_files_with_password_key(self):
        self.assertEqual(poster.credential_password({"password": "private-value"}), "private-value")

    def test_keeps_legacy_pw_key_compatibility(self):
        self.assertEqual(poster.credential_password({"pw": "legacy-value"}), "legacy-value")

    def test_missing_password_fails_closed(self):
        with self.assertRaises(ValueError):
            poster.credential_password({"username": "x"})


if __name__ == "__main__":
    unittest.main()
