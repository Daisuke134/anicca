#!/usr/bin/env python3
"""Regression test for warmer.py's promotion guard (2026-07-17 session-churn fix).

Real bug found in production ~/.cloak/ig-warmup-aiclips_world_hq.json: log ends at
day=3/date=2026-07-15 (clean success), but aborts has a LATER entry
date=2026-07-16 "not logged in". The OLD code only checked state_summary()'s
day (from log[-1]) and a "banned" flag scanning for the literal word "ban" --
a login abort that is NOT a ban signal was silently ignored, so warmer.py
would promote warming->ready off a stale day=3 even though the account failed
to log in the very next day. That is the same class of bug that causes
session churn: promoting an account whose session is not actually healthy.

Fix: recent_abort_after_last_log(st) must return True whenever the most recent
aborts entry is dated after the most recent log entry, and main()'s promotion
branch must hold (not promote) whenever that guard is True, even if
day >= PROMOTE_DAY and banned is False.

recent_abort_after_last_log does not exist yet on the pre-fix warmer.py --
this test MUST FAIL (AttributeError) until the fix lands.
"""
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

CLIP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKETING_ENGINE_DIR = os.path.join(os.path.dirname(CLIP_DIR), "marketing-engine")
sys.path.insert(0, MARKETING_ENGINE_DIR)

import warmer  # noqa: E402


class TestWarmingStatusVocabulary(unittest.TestCase):
    def test_pick_target_accepts_warming_day1(self):
        account = {
            "handle": "day1",
            "status": "warming_day1",
            "started_warming": "2026-07-19",
        }
        target, changed = warmer.pick_target([account])
        self.assertIs(target, account)
        self.assertFalse(changed)

REAL_BUG_STATE = {
    "handle": "aiclips_world_hq",
    "log": [
        {"date": "2026-07-13", "day": 1, "actions": {"reels": 6, "scrolls": 5}, "verified": {"reels_played": 6}},
        {"date": "2026-07-14", "day": 2, "actions": {"reels": 8, "scrolls": 6}, "verified": {"reels_played": 8}},
        {"date": "2026-07-15", "day": 3, "actions": {"reels": 8, "scrolls": 6}, "verified": {"reels_played": 8}},
    ],
    "aborts": [
        {"date": "2026-07-16", "day": 4, "actions": {}, "verified": {}, "ABORT": "not logged in"},
    ],
}


class TestRecentAbortGuard(unittest.TestCase):
    def test_day3_log_then_abort_the_next_day_blocks_promotion(self):
        """The exact real-world shape from ig-warmup-aiclips_world_hq.json."""
        day, banned, _ = warmer.state_summary(REAL_BUG_STATE)
        self.assertEqual(day, 3)
        self.assertFalse(banned, "a plain 'not logged in' abort must not trip the ban-signal detector")
        self.assertTrue(
            warmer.recent_abort_after_last_log(REAL_BUG_STATE),
            "an abort dated AFTER the last successful log entry must block promotion "
            "even though day(3) >= PROMOTE_DAY(3) and banned is False",
        )

    def test_no_aborts_never_blocks(self):
        st = {"log": [{"date": "2026-07-15", "day": 3}], "aborts": []}
        self.assertFalse(warmer.recent_abort_after_last_log(st))

    def test_abort_before_last_log_does_not_block(self):
        """An old abort that happened BEFORE the account's most recent success (e.g. a
        one-off blip that was later followed by a clean successful day) must not hold
        promotion hostage forever."""
        st = {
            "log": [
                {"date": "2026-07-10", "day": 1},
                {"date": "2026-07-15", "day": 3},
            ],
            "aborts": [{"date": "2026-07-11", "day": 2, "ABORT": "not logged in"}],
        }
        self.assertFalse(warmer.recent_abort_after_last_log(st))

    def test_only_aborts_no_log_blocks(self):
        st = {"log": [], "aborts": [{"date": "2026-07-16", "day": 1, "ABORT": "not logged in"}]}
        self.assertTrue(warmer.recent_abort_after_last_log(st))


class TestMainDoesNotPromoteOnRecentAbort(unittest.TestCase):
    """End-to-end: main() must leave status=="warming" (not promote to "ready") when the
    account's warmup log shows day>=3 but the most recent event is a post-day-3 abort."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="warmer_test_")
        self.fake_home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.fake_home, ".cloak"), exist_ok=True)
        self.accts_path = os.path.join(self.tmp, "clip-accounts.json")
        accts = [
            {
                "handle": "aiclips_world_hq",
                "profile": "clip-en9",
                "port": 65432,  # nothing listens here -> browser_up() is False, no creds -> clean skip
                "status": "warming",
                "started_warming": "2026-07-13",
            }
        ]
        with open(self.accts_path, "w") as f:
            json.dump(accts, f)
        warmup_path = os.path.join(self.fake_home, ".cloak", "ig-warmup-aiclips_world_hq.json")
        with open(warmup_path, "w") as f:
            json.dump(REAL_BUG_STATE, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_status_stays_warming_not_promoted(self):
        env = dict(os.environ)
        env["HOME"] = self.fake_home
        r = subprocess.run(
            [sys.executable, os.path.join(MARKETING_ENGINE_DIR, "warmer.py"), self.accts_path],
            env=env, capture_output=True, text=True, timeout=60,
        )
        with open(self.accts_path) as f:
            accts_after = json.load(f)
        status = accts_after[0]["status"]
        self.assertEqual(
            status, "warming",
            f"must NOT promote to ready when a login abort was recorded after the last "
            f"successful log day (rc={r.returncode}, stdout={r.stdout!r}, stderr={r.stderr!r})",
        )


class FakeClient:
    def __init__(self, fail_feed=False):
        self.fail_feed = fail_feed
        self.login_calls = []
        self.load_calls = []
        self.feed_calls = 0
        self.dump_calls = []

    def login(self, username, password):
        self.login_calls.append((username, password))

    def load_settings(self, path):
        self.load_calls.append(path)

    def get_timeline_feed(self):
        self.feed_calls += 1
        if self.fail_feed:
            raise RuntimeError("dead session")
        return {"feed_items": [1]}

    def dump_settings(self, path):
        self.dump_calls.append(path)
        with open(path, "w") as f:
            json.dump({"cookies": {"sessionid": "saved"}}, f)
        return True


class TestGoldenSessionLifecycle(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="golden_session_test_")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".cloak"), exist_ok=True)
        self.handle = "aged_account"
        with open(os.path.join(self.home, ".cloak", f"ig-{self.handle}.json"), "w") as f:
            json.dump({"username": self.handle, "pw": "secret"}, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_day_count_uses_creation_day_as_day1(self):
        today = warmer.datetime.date(2026, 7, 19)
        self.assertEqual(warmer.warming_day("2026-07-19", today), 1)
        self.assertEqual(warmer.warming_day("2026-07-18", today), 2)
        self.assertEqual(warmer.warming_day("2026-07-17", today), 3)

    def test_first_day3_session_logs_in_feeds_and_dumps_once(self):
        client = FakeClient()
        result = warmer.establish_golden_session(
            self.handle, home=self.home, client_factory=lambda: client
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["login_performed"])
        self.assertEqual(client.login_calls, [(self.handle, "secret")])
        self.assertEqual(client.feed_calls, 1)
        self.assertEqual(len(client.dump_calls), 1)

    def test_existing_settings_are_loaded_without_password_relogin(self):
        settings = os.path.join(self.home, ".cloak", f"instagrapi-{self.handle}.json")
        with open(settings, "w") as f:
            json.dump({"cookies": {"sessionid": "saved"}}, f)
        client = FakeClient()
        result = warmer.establish_golden_session(
            self.handle, home=self.home, client_factory=lambda: client
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["login_performed"])
        self.assertEqual(client.login_calls, [])
        self.assertEqual(client.load_calls, [settings])
        self.assertEqual(client.feed_calls, 1)

    def test_dead_saved_session_never_falls_back_to_password_login(self):
        settings = os.path.join(self.home, ".cloak", f"instagrapi-{self.handle}.json")
        with open(settings, "w") as f:
            json.dump({"cookies": {"sessionid": "dead"}}, f)
        client = FakeClient(fail_feed=True)
        result = warmer.establish_golden_session(
            self.handle, home=self.home, client_factory=lambda: client
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["terminal"])
        self.assertEqual(client.login_calls, [])
        self.assertEqual(client.load_calls, [settings])

    def test_attempt_marker_blocks_second_password_login(self):
        marker = os.path.join(self.home, ".cloak", f".golden-session-attempted-{self.handle}")
        with open(marker, "w") as f:
            f.write("already-attempted\n")
        client = FakeClient()
        result = warmer.establish_golden_session(
            self.handle, home=self.home, client_factory=lambda: client
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["terminal"])
        self.assertEqual(client.login_calls, [])


class TestMainDayGate(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="warm_day_gate_test_")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".cloak"), exist_ok=True)
        self.accounts = os.path.join(self.tmp, "accounts.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_account(self, started_warming):
        with open(self.accounts, "w") as f:
            json.dump([{
                "handle": "fresh_account",
                "profile": "clip-en1",
                "port": 65431,
                "status": "warming",
                "session_owner": "browser",
                "started_warming": started_warming,
            }], f)

    def run_main(self, session_result):
        with mock.patch.dict(os.environ, {"HOME": self.home}), \
             mock.patch.object(sys, "argv", ["warmer.py", self.accounts]), \
             mock.patch.object(warmer, "browser_up", return_value=False), \
             mock.patch.object(warmer, "load_warmup_state", return_value={"log": [], "aborts": []}), \
             mock.patch.object(warmer, "append_warmlog"), \
             mock.patch.object(warmer, "establish_golden_session", return_value=session_result) as establish:
            rc = warmer.main()
        with open(self.accounts) as f:
            account = json.load(f)[0]
        return rc, account, establish

    def test_day2_does_not_create_golden_session(self):
        self.write_account((warmer.datetime.date.today() - warmer.datetime.timedelta(days=1)).isoformat())
        rc, account, establish = self.run_main({"ok": True})
        self.assertEqual(rc, 0)
        self.assertEqual(account["status"], "warming")
        self.assertEqual(account["session_owner"], "browser")
        establish.assert_not_called()

    def test_day3_creates_session_then_promotes(self):
        self.write_account((warmer.datetime.date.today() - warmer.datetime.timedelta(days=2)).isoformat())
        rc, account, establish = self.run_main({"ok": True, "login_performed": True})
        self.assertEqual(rc, 0)
        self.assertEqual(account["status"], "ready")
        self.assertEqual(account["session_owner"], "instagrapi")
        establish.assert_called_once_with("fresh_account", warming_day_value=3)


if __name__ == "__main__":
    unittest.main()
