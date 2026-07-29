#!/usr/bin/env python3
"""Tests for poster.py's keepalive_main() — the read-only golden-session probe fired by
session_vault_tick.sh every 30 min (v24 #12). It must NEVER log in: a dead session is self-heal's
job (replace the account), not keepalive's.

Mocks instagrapi.Client entirely (no network, no real IG account touched). Mirrors
test_login_resilient.py's style.
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

MARKETING_ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/marketing-engine"
sys.path.insert(0, MARKETING_ENGINE_DIR)

import poster as ip  # noqa: E402


class TestKeepaliveMain(unittest.TestCase):

    def setUp(self):
        self.fake_client = mock.MagicMock()
        self.fake_client.load_settings = mock.MagicMock()
        self.fake_client.dump_settings = mock.MagicMock()
        self.fake_client.get_timeline_feed = mock.MagicMock(return_value={})
        self.fake_client.sync_launcher = mock.MagicMock(return_value={})
        self.fake_client.account_info = mock.MagicMock(
            return_value=mock.MagicMock(username="h")
        )

    def test_keepalive_main_no_settings_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = ip.keepalive_main("nosuch", settings_path=os.path.join(tmp, "absent.json"))
            self.assertFalse(res["alive"])
            self.assertIn("no saved session", res["error"])

    def test_keepalive_main_alive_dumps_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = os.path.join(tmp, "s.json")
            with open(settings, "w") as f:
                f.write("{}")
            res = ip.keepalive_main("h", settings_path=settings, client_factory=lambda: self.fake_client)
            self.assertTrue(res["alive"])
            self.assertTrue(res["feed_ok"])
            self.assertTrue(res["ping_ok"])
            self.assertTrue(res["identity_ok"])
            self.fake_client.dump_settings.assert_called_once_with(settings)

    def test_keepalive_main_exact_identity_atomically_recovers_poisoned_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = os.path.join(tmp, "s.json")
            accounts = os.path.join(tmp, "accounts.json")
            with open(settings, "w") as f:
                f.write("{}")
            with open(accounts, "w") as f:
                json.dump([
                    {
                        "handle": "h",
                        "status": "poisoned_manual_backup",
                        "session_owner": "instagrapi",
                        "poisoned_reason": "old challenge",
                        "poisoned_at": "2026-07-29T01:16Z",
                    },
                    {"handle": "other", "status": "ready"},
                ], f)
            os.chmod(accounts, 0o600)

            res = ip.keepalive_main(
                "h",
                settings_path=settings,
                accounts_path=accounts,
                client_factory=lambda: self.fake_client,
            )

            with open(accounts, encoding="utf-8") as source:
                rows = json.load(source)
            self.assertTrue(res["alive"])
            self.assertTrue(res["recovered"])
            self.assertEqual(rows[0]["status"], "ready")
            self.assertEqual(rows[0]["session_owner"], "instagrapi")
            self.assertNotIn("poisoned_reason", rows[0])
            self.assertNotIn("poisoned_at", rows[0])
            self.assertRegex(rows[0]["recovered_at"], r"^\d{4}-\d{2}-\d{2}T")
            self.assertEqual(rows[1], {"handle": "other", "status": "ready"})
            self.assertEqual(os.stat(accounts).st_mode & 0o777, 0o600)

    def test_keepalive_main_identity_mismatch_never_recovers_or_dumps(self):
        self.fake_client.account_info.return_value = mock.MagicMock(username="wrong")
        with tempfile.TemporaryDirectory() as tmp:
            settings = os.path.join(tmp, "s.json")
            accounts = os.path.join(tmp, "accounts.json")
            with open(settings, "w") as f:
                f.write("{}")
            original = [{
                "handle": "h",
                "status": "poisoned_manual_backup",
                "poisoned_reason": "old challenge",
            }]
            with open(accounts, "w") as f:
                json.dump(original, f)

            res = ip.keepalive_main(
                "h",
                settings_path=settings,
                accounts_path=accounts,
                client_factory=lambda: self.fake_client,
            )

            self.assertFalse(res["alive"])
            self.assertFalse(res["identity_ok"])
            with open(accounts, encoding="utf-8") as source:
                self.assertEqual(json.load(source), original)
            self.fake_client.dump_settings.assert_not_called()

    def test_keepalive_main_login_required_never_relogins(self):
        from instagrapi.exceptions import LoginRequired
        self.fake_client.get_timeline_feed = mock.MagicMock(side_effect=LoginRequired())
        with tempfile.TemporaryDirectory() as tmp:
            settings = os.path.join(tmp, "s.json")
            with open(settings, "w") as f:
                f.write("{}")
            res = ip.keepalive_main("h", settings_path=settings, client_factory=lambda: self.fake_client)
            self.assertFalse(res["alive"])
            self.fake_client.login.assert_not_called()
            self.fake_client.login_by_sessionid.assert_not_called()
            self.assertNotEqual(res.get("poisoned"), True)

    def test_keepalive_main_challenge_marks_poisoned(self):
        from instagrapi.exceptions import ChallengeRequired
        self.fake_client.get_timeline_feed = mock.MagicMock(side_effect=ChallengeRequired())
        with tempfile.TemporaryDirectory() as tmp:
            settings = os.path.join(tmp, "s.json")
            with open(settings, "w") as f:
                f.write("{}")
            accounts = os.path.join(tmp, "accounts.json")
            with open(accounts, "w") as f:
                json.dump([{"handle": "h", "status": "ready"}], f)
            res = ip.keepalive_main(
                "h", settings_path=settings, accounts_path=accounts,
                client_factory=lambda: self.fake_client)
            self.assertFalse(res["alive"])
            self.assertTrue(res["poisoned"])
            with open(accounts, encoding="utf-8") as source:
                self.assertEqual(
                    json.load(source)[0]["status"],
                    "poisoned_manual_backup",
                )
            self.fake_client.login.assert_not_called()


if __name__ == "__main__":
    unittest.main()
