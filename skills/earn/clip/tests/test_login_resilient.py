#!/usr/bin/env python3
"""Tests for poster.py's session-preserving login policy (SSOT: docs/earn/
ig-4account-reels-carousel-loop-plan.md v22/v23/v24 — "never let the golden session die, never
relogin once it has").

Covers the three behavioral guarantees required by that SSOT:
  1. login_resilient() never calls cl.login() (password) while a saved session is alive.
  2. A bloks ChallengeRequired at any tier marks the account poisoned in clip-accounts.json and
     returns without EVER attempting a password relogin.
  3. keepalive() is a read-only probe that returns False only on a confirmed LoginRequired.

Mocks instagrapi.Client entirely (no network, no real IG account touched).
"""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

MARKETING_ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/marketing-engine"
sys.path.insert(0, MARKETING_ENGINE_DIR)

import poster as ip  # noqa: E402
from instagrapi.exceptions import ChallengeRequired, LoginRequired, RateLimitError  # noqa: E402


def _write_accounts(tmpdir, handle, session_owner=None, status="ready"):
    path = os.path.join(tmpdir, "clip-accounts.json")
    entry = {"handle": handle, "status": status}
    if session_owner is not None:
        entry["session_owner"] = session_owner
    with open(path, "w") as f:
        json.dump([entry], f)
    return path


class TestTier1NeverRelogins(unittest.TestCase):
    """Guarantee 1: if the saved instagrapi session is alive, password login must never fire."""

    def test_alive_session_never_calls_password_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "instagrapi-h.json")
            with open(settings_path, "w") as f:
                json.dump({"uuids": {}}, f)  # any non-empty settings file = "session existed"
            accounts_path = _write_accounts(tmp, "h")

            cl = mock.MagicMock()
            cl.load_settings = mock.MagicMock()
            cl.get_timeline_feed = mock.MagicMock(return_value={})  # tier1 verifies clean
            cl.login = mock.MagicMock()  # password login — must NEVER be called

            res = {"handle": "h", "outcome": "failed"}
            ok = ip.login_resilient(cl, "h", 9222, res, settings_path=settings_path, accounts_path=accounts_path)

            self.assertTrue(ok)
            cl.login.assert_not_called()
            cl.load_settings.assert_called_once_with(settings_path)

    def test_tier1_success_dumps_refreshed_settings(self):
        # gold standard (alsk1992 ig.py L556-708): a successful tier1 read must persist any
        # server-rotated cookies back to disk, so the golden session stays fresh between runs.
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "instagrapi-h.json")
            with open(settings_path, "w") as f:
                json.dump({"uuids": {}}, f)
            accounts_path = _write_accounts(tmp, "h")

            cl = mock.MagicMock()
            cl.load_settings = mock.MagicMock()
            cl.get_timeline_feed = mock.MagicMock(return_value={})  # tier1 verifies clean
            cl.dump_settings = mock.MagicMock()
            cl.login = mock.MagicMock()  # password login — must NEVER be called

            res = {"handle": "h", "outcome": "failed"}
            ok = ip.login_resilient(cl, "h", 9222, res, settings_path=settings_path, accounts_path=accounts_path)

            self.assertTrue(ok)
            cl.login.assert_not_called()
            cl.dump_settings.assert_called_once_with(settings_path)

    def test_dead_session_with_existing_settings_refuses_password_relogin(self):
        # v23 core finding: a saved session that died is NOT a green light for password login —
        # that relogin is exactly what trips bloks. login_resilient must refuse, not relogin.
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "instagrapi-h.json")
            with open(settings_path, "w") as f:
                json.dump({"uuids": {}}, f)
            # session_owner=instagrapi so tier2 (browser sessionid) is also skipped, isolating the
            # assertion to "tier1 dead + settings existed -> no tier3", per v22.
            accounts_path = _write_accounts(tmp, "h", session_owner="instagrapi")

            cl = mock.MagicMock()
            cl.load_settings = mock.MagicMock()
            cl.get_timeline_feed = mock.MagicMock(side_effect=LoginRequired("dead"))
            cl.login = mock.MagicMock()  # password login — must NEVER be called

            res = {"handle": "h", "outcome": "failed"}
            ok = ip.login_resilient(cl, "h", 9222, res, settings_path=settings_path, accounts_path=accounts_path)

            self.assertFalse(ok)
            cl.login.assert_not_called()
            self.assertIn("refusing relogin", res["error"])


class TestBloksNeverResuscitated(unittest.TestCase):
    """Guarantee 2: bloks ChallengeRequired at any tier marks the account poisoned and never
    retries login on it (v23/v24 — the account is dead, only self-heal replaces it)."""

    def test_tier1_bloks_marks_poisoned_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "instagrapi-h.json")
            with open(settings_path, "w") as f:
                json.dump({"uuids": {}}, f)
            accounts_path = _write_accounts(tmp, "h", session_owner="instagrapi", status="ready")

            cl = mock.MagicMock()
            cl.load_settings = mock.MagicMock()
            cl.get_timeline_feed = mock.MagicMock(side_effect=ChallengeRequired("bloks"))
            cl.login = mock.MagicMock()

            res = {"handle": "h", "outcome": "failed"}
            ok = ip.login_resilient(cl, "h", 9222, res, settings_path=settings_path, accounts_path=accounts_path)

            self.assertFalse(ok)
            self.assertTrue(res.get("poisoned"))
            cl.login.assert_not_called()

            accounts = json.load(open(accounts_path))
            self.assertEqual(accounts[0]["status"], "poisoned_manual_backup")
            self.assertIn("poisoned_reason", accounts[0])

    def test_tier3_bloks_on_fresh_account_marks_poisoned(self):
        # No settings file at all -> genuinely fresh account -> tier3 is allowed to fire once.
        # If IT hits bloks, poison immediately (do not retry).
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "instagrapi-h.json")  # deliberately not created
            accounts_path = _write_accounts(tmp, "h", session_owner="browser", status="provisioned_pending_live_post")
            creds_path = os.path.join(tmp, "ig-h.json")
            with open(creds_path, "w") as f:
                json.dump({"username": "h", "pw": "x"}, f)

            cl = mock.MagicMock()
            cl.login = mock.MagicMock(side_effect=ChallengeRequired("bloks"))
            cl.dump_settings = mock.MagicMock()

            res = {"handle": "h", "outcome": "failed"}
            with mock.patch.object(ip, "get_sessionid", return_value=(None, None)), \
                 mock.patch.object(ip, "C", side_effect=lambda p: {
                     "~/.cloak/.last-pwlogin-h": os.path.join(tmp, ".last-pwlogin-h"),
                     "~/.cloak/ig-h.json": creds_path,
                 }.get(p, os.path.expanduser(p))):
                ok = ip.login_resilient(cl, "h", 9222, res, settings_path=settings_path, accounts_path=accounts_path)

            self.assertFalse(ok)
            self.assertTrue(res.get("poisoned"))
            cl.dump_settings.assert_not_called()
            accounts = json.load(open(accounts_path))
            self.assertEqual(accounts[0]["status"], "poisoned_manual_backup")


class TestKeepalive(unittest.TestCase):
    """Guarantee 3: keepalive() is read-only and returns False only on confirmed LoginRequired."""

    def test_keepalive_true_when_feed_read_succeeds(self):
        cl = mock.MagicMock()
        cl.get_timeline_feed = mock.MagicMock(return_value={})
        self.assertTrue(ip.keepalive(cl))

    def test_keepalive_false_on_login_required(self):
        cl = mock.MagicMock()
        cl.get_timeline_feed = mock.MagicMock(side_effect=LoginRequired("dead"))
        self.assertFalse(ip.keepalive(cl))

    def test_keepalive_does_not_write_or_relogin_on_transient_error(self):
        # A non-LoginRequired hiccup (e.g. rate limit) must NOT be treated as death -- must not
        # trigger any login()/dump_settings() call from keepalive itself.
        cl = mock.MagicMock()
        cl.get_timeline_feed = mock.MagicMock(side_effect=RateLimitError("429"))
        cl.login = mock.MagicMock()
        result = ip.keepalive(cl)
        self.assertTrue(result)
        cl.login.assert_not_called()

    def test_gentle_ping_uses_sync_launcher_and_detects_login_required(self):
        cl = mock.MagicMock()
        cl.sync_launcher = mock.MagicMock(side_effect=LoginRequired("dead"))
        self.assertFalse(ip.gentle_ping(cl))
        cl.sync_launcher.assert_called_once_with(login=False)

    def test_gentle_ping_true_when_sync_launcher_succeeds(self):
        cl = mock.MagicMock()
        cl.sync_launcher = mock.MagicMock(return_value={})
        self.assertTrue(ip.gentle_ping(cl))

    def test_keepalive_reraises_challenge_required(self):
        # bloks poison signal during a probe must propagate, not read as "alive" (v24 #12).
        cl = mock.MagicMock()
        cl.get_timeline_feed = mock.MagicMock(side_effect=ChallengeRequired())
        with self.assertRaises(ChallengeRequired):
            ip.keepalive(cl)

    def test_gentle_ping_reraises_challenge_required(self):
        cl = mock.MagicMock()
        cl.sync_launcher = mock.MagicMock(side_effect=ChallengeRequired())
        with self.assertRaises(ChallengeRequired):
            ip.gentle_ping(cl)

    def test_keepalive_transient_error_still_true(self):
        cl = mock.MagicMock()
        cl.get_timeline_feed = mock.MagicMock(side_effect=RuntimeError("transient network blip"))
        self.assertTrue(ip.keepalive(cl))


if __name__ == "__main__":
    unittest.main()
