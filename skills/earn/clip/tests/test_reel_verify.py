#!/usr/bin/env python3
"""RED-phase unit tests for reel_verify.py's pure functions (VCSDD Phase 2a).

Covers PROP-001, PROP-002, PROP-003, PROP-004(a), PROP-010 from
.vcsdd/features/clip-post-verify-hardening/specs/verification-architecture.md
(anicca-project repo). reel_verify.py does not exist yet — these tests MUST FAIL
(ImportError) until Phase 2b (GREEN) implements it.

Run: python3 -m pytest tests/test_reel_verify.py -v
  or: python3 tests/test_reel_verify.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reel_verify  # noqa: E402


class TestReadsStable(unittest.TestCase):
    """PROP-001: _reads_stable(latest, previous) -> bool, set equality of two href lists."""

    def test_identical_lists_are_stable(self):
        self.assertTrue(reel_verify._reads_stable(["a", "b"], ["a", "b"]))

    def test_different_lists_are_not_stable(self):
        self.assertFalse(reel_verify._reads_stable(["a", "b"], ["a"]))

    def test_order_independent(self):
        # set equality, order must not matter
        self.assertTrue(reel_verify._reads_stable(["b", "a"], ["a", "b"]))


class TestStabilizeReads(unittest.TestCase):
    """PROP-001/002: stabilize_reads(read_fn, max_reads=3, settle_s=5) ->
    {"stable": bool, "hrefs": list[str] or None}.
    Exactly 2 pair-comparisons within exactly 3 reads: read1-vs-read2, read2-vs-read3."""

    def test_stabilizes_on_second_pair(self):
        # reads = [["a"], ["a","b"], ["a","b"]] -- read2==read3 -> stable=True, hrefs=["a","b"]
        reads = iter([["a"], ["a", "b"], ["a", "b"]])
        result = reel_verify.stabilize_reads(lambda: next(reads), max_reads=3, settle_s=0)
        self.assertTrue(result["stable"])
        self.assertEqual(set(result["hrefs"]), {"a", "b"})

    def test_exhausts_to_inconclusive(self):
        # reads = [["a"], ["b"], ["c"]] -- no consecutive pair matches -> stable=False, hrefs=None
        reads = iter([["a"], ["b"], ["c"]])
        result = reel_verify.stabilize_reads(lambda: next(reads), max_reads=3, settle_s=0)
        self.assertFalse(result["stable"])
        # PROP-002: explicitly hrefs is None, NOT the last read ["c"] used as if trustworthy
        self.assertIsNone(result["hrefs"])

    def test_stabilizes_on_first_pair_stops_early(self):
        # reads = [["a","b"], ["a","b"], ...] -- read1==read2, must stop at 2 reads (not consume a 3rd)
        calls = []

        def read_fn():
            calls.append(1)
            return ["a", "b"]

        result = reel_verify.stabilize_reads(read_fn, max_reads=3, settle_s=0)
        self.assertTrue(result["stable"])
        self.assertEqual(len(calls), 2, "must stop after read1==read2, not consume a 3rd read")


class TestDiffNewHref(unittest.TestCase):
    """PROP-004: diff_new_href(before_hrefs, after_hrefs) -> str or None."""

    def test_returns_new_href_not_in_before(self):
        result = reel_verify.diff_new_href(["/a/", "/b/"], ["/a/", "/b/", "/c/"])
        self.assertEqual(result, "/c/")

    def test_returns_none_when_no_new_href(self):
        result = reel_verify.diff_new_href(["/a/", "/b/"], ["/a/", "/b/"])
        self.assertIsNone(result)


class TestClassifyOutcome(unittest.TestCase):
    """PROP-003/PROP-004(a): classify_outcome(candidate, reconfirm_hrefs, before_count) ->
    {"outcome": str, "published": bool, "post_url": str or None}. Exhaustive 3-branch coverage."""

    def test_published_when_candidate_present_and_count_plus_one(self):
        r = reel_verify.classify_outcome("X", ["X", "a", "b"], 2)
        self.assertEqual(r["outcome"], "published")
        self.assertTrue(r["published"])
        self.assertEqual(r["post_url"], "X")

    def test_unverified_when_candidate_missing_from_reconfirm(self):
        r = reel_verify.classify_outcome("X", ["a", "b"], 2)
        self.assertEqual(r["outcome"], "unverified")
        self.assertFalse(r["published"])
        self.assertIsNone(r["post_url"])

    def test_unverified_when_count_did_not_net_increase(self):
        # X present but len(reconfirm)=2 != before_count(2)+1 -- count didn't net-increase
        r = reel_verify.classify_outcome("X", ["X", "a"], 2)
        self.assertEqual(r["outcome"], "unverified")
        self.assertFalse(r["published"])
        self.assertIsNone(r["post_url"])

    def test_failed_when_loop_exhausted_no_candidate(self):
        r = reel_verify.classify_outcome(None, None, 2)
        self.assertEqual(r["outcome"], "failed")
        self.assertFalse(r["published"])
        self.assertIsNone(r["post_url"])


class TestSelectConfirmedHref(unittest.TestCase):
    """PROP-006/PROP-010: select_confirmed_href(candidate_hrefs, candidate_page_texts, expected_token)
    -> str or None. Exact substring containment check on the token; full 3-way branch coverage
    (0 / exactly-1 / 2+ matches)."""

    def test_exactly_one_match_returns_that_href(self):
        r = reel_verify.select_confirmed_href(
            ["/A/", "/B/"],
            {"/A/": "some caption text ...#c4f2a91b7c3... #hashtags", "/B/": "unrelated other post text"},
            "#c4f2a91b7c3",
        )
        self.assertEqual(r, "/A/")

    def test_zero_matches_returns_none(self):
        r = reel_verify.select_confirmed_href(
            ["/A/", "/B/"],
            {"/A/": "unrelated text", "/B/": "also unrelated"},
            "#c4f2a91b7c3",
        )
        self.assertIsNone(r)

    def test_two_plus_matches_returns_none_not_arbitrary_pick(self):
        # PROP-010: BOTH candidates' page text happens to contain the SAME token (contrived but possible)
        r = reel_verify.select_confirmed_href(
            ["/A/", "/B/"],
            {"/A/": "...#c4f2a91b7c3...", "/B/": "...#c4f2a91b7c3..."},
            "#c4f2a91b7c3",
        )
        self.assertIsNone(r)


if __name__ == "__main__":
    unittest.main()
