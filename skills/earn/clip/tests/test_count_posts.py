#!/usr/bin/env python3
"""RED-phase unit tests for count_posts.py (VCSDD Phase 2a, PROP-007).

REQ-009: monitor.sh's posts-recorded count must be URL-deduplicated with a null-guard
on both old and new format ledger lines — never a raw line count. Tested against a
FROZEN fixture (tests/fixtures/ledger-2026-07-03-snapshot.jsonl), never the live,
ever-growing ~/.local/state/life-manager/state/clip-earn-ledger.jsonl (iteration-3 FIND-001).

count_posts.py does not exist yet — this test MUST FAIL (ImportError) until Phase 2b.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import count_posts  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "ledger-2026-07-03-snapshot.jsonl")


class TestCountConfirmedPosts(unittest.TestCase):
    def test_frozen_4line_snapshot_counts_2(self):
        """The real historical incident: line2/line3 share the IDENTICAL post_url
        (true-positive + its false-positive duplicate); line4 is the null-post_url
        correction. URL-dedup must collapse this to 2, not 3 (a raw-count bug) or 1."""
        with open(FIXTURE) as f:
            lines = f.readlines()
        self.assertEqual(count_posts.count_confirmed_posts(lines), 2)

    def test_new_format_different_urls_counts_both(self):
        lines = [
            json.dumps({"status": "posted", "post_url": "https://x/A/"}),
            json.dumps({"status": "unverified", "post_url": None}),
        ]
        self.assertEqual(count_posts.count_confirmed_posts(lines), 1)

    def test_null_post_url_on_posted_status_never_counted(self):
        """Regression for the exact malformed shape a count-only self-heal bug WOULD
        produce: a status:"posted" line with post_url:null must NEVER be counted,
        even though its status field says "posted"."""
        lines = [
            json.dumps({"status": "posted", "post_url": None}),
            json.dumps({"status": "posted", "post_url": "https://x/REAL/"}),
        ]
        self.assertEqual(count_posts.count_confirmed_posts(lines), 1)

    def test_old_format_false_positive_corrected_excluded(self):
        lines = [
            json.dumps({"post_url": "https://x/A/"}),
            json.dumps({"post_url": "https://x/A/", "false_positive_corrected": True}),
        ]
        # both share the same URL anyway (dedup would collapse to 1), but the flagged
        # line must be excluded from consideration entirely per REQ-009 step 2
        self.assertEqual(count_posts.count_confirmed_posts(lines), 1)

    def test_empty_ledger_counts_zero(self):
        self.assertEqual(count_posts.count_confirmed_posts([]), 0)


if __name__ == "__main__":
    unittest.main()
