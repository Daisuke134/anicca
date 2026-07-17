#!/usr/bin/env python3
"""Regression test for warm_step.py's promotion guard (2026-07-17 session-churn fix).

Real bug found in production ~/.cloak/ig-warmup-aiclips_world_hq.json: log ends at
day=3/date=2026-07-15 (clean success), but aborts has a LATER entry
date=2026-07-16 "not logged in". The OLD code only checked state_summary()'s
day (from log[-1]) and a "banned" flag scanning for the literal word "ban" --
a login abort that is NOT a ban signal was silently ignored, so warm_step.py
would promote warming->ready off a stale day=3 even though the account failed
to log in the very next day. That is the same class of bug that causes
session churn: promoting an account whose session is not actually healthy.

Fix: recent_abort_after_last_log(st) must return True whenever the most recent
aborts entry is dated after the most recent log entry, and main()'s promotion
branch must hold (not promote) whenever that guard is True, even if
day >= PROMOTE_DAY and banned is False.

recent_abort_after_last_log does not exist yet on the pre-fix warm_step.py --
this test MUST FAIL (AttributeError) until the fix lands.
"""
import json
import os
import subprocess
import sys
import unittest

CLIP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLIP_DIR)

import warm_step  # noqa: E402

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
        day, banned, _ = warm_step.state_summary(REAL_BUG_STATE)
        self.assertEqual(day, 3)
        self.assertFalse(banned, "a plain 'not logged in' abort must not trip the ban-signal detector")
        self.assertTrue(
            warm_step.recent_abort_after_last_log(REAL_BUG_STATE),
            "an abort dated AFTER the last successful log entry must block promotion "
            "even though day(3) >= PROMOTE_DAY(3) and banned is False",
        )

    def test_no_aborts_never_blocks(self):
        st = {"log": [{"date": "2026-07-15", "day": 3}], "aborts": []}
        self.assertFalse(warm_step.recent_abort_after_last_log(st))

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
        self.assertFalse(warm_step.recent_abort_after_last_log(st))

    def test_only_aborts_no_log_blocks(self):
        st = {"log": [], "aborts": [{"date": "2026-07-16", "day": 1, "ABORT": "not logged in"}]}
        self.assertTrue(warm_step.recent_abort_after_last_log(st))


class TestMainDoesNotPromoteOnRecentAbort(unittest.TestCase):
    """End-to-end: main() must leave status=="warming" (not promote to "ready") when the
    account's warmup log shows day>=3 but the most recent event is a post-day-3 abort."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="warm_step_test_")
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
            [sys.executable, os.path.join(CLIP_DIR, "warm_step.py"), self.accts_path],
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


if __name__ == "__main__":
    unittest.main()
