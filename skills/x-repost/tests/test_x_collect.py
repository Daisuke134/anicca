from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "x_collect.py"
SPEC = importlib.util.spec_from_file_location("x_collect", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class XCollectTests(unittest.TestCase):
    def test_public_count_keeps_unknown_distinct_from_zero(self) -> None:
        self.assertEqual(MODULE.parse_public_count("1 Follower"), 1)
        self.assertEqual(MODULE.parse_public_count("2.5K Followers"), 2500)
        self.assertIsNone(MODULE.parse_public_count("Followers unavailable"))

    def test_daily_snapshot_separates_original_reply_and_affiliate(self) -> None:
        now = datetime(2026, 8, 22, tzinfo=timezone.utc)
        rows = [
            {"posted_at": now.isoformat(), "post_url": "https://x.com/me/status/1",
             "kind": "original", "engagement": {"views": 20, "likes": 1,
             "replies": 0, "reposts": 0, "bookmarks": 0}},
            {"posted_at": now.isoformat(), "post_url": "https://x.com/me/status/2",
             "kind": "affiliate_original"},
            {"posted_at": now.isoformat(), "post_url": None, "kind": "reply"},
        ]
        with tempfile.TemporaryDirectory() as root:
            posted = Path(root) / "posted.jsonl"
            snapshot = MODULE.write_daily_snapshot(
                posted, rows,
                {"followers": 1, "profile_visits": None,
                 "profile_visits_state": "UNAVAILABLE_X_PREMIUM_REQUIRED"}, now,
            )
            persisted = json.loads((Path(root) / "metrics/daily/2026-08-22.json").read_text())
        self.assertEqual(snapshot, persisted)
        self.assertEqual(snapshot["published_post_count"], 2)
        self.assertEqual(snapshot["by_kind"]["original"]["views"], 20)
        self.assertEqual(snapshot["by_kind"]["affiliate_original"]["measured_post_count"], 0)
        self.assertNotIn("reply", snapshot["by_kind"])
        self.assertIsNone(snapshot["profile"]["profile_visits"])


if __name__ == "__main__":
    unittest.main()
