#!/usr/bin/env python3
"""Shared pure verification logic for the clip-earn IG-reel posting/self-heal pipeline.

Used by both instagrapi_post.py (this directory's scripts/, the free instagrapi-based
poster; SHARED-1 retired the earlier web-composer poster) and this directory's self-heal
driver (self_heal.py). One implementation, no duplicate/drifting logic across the two call sites.

Per .vcsdd/features/clip-post-verify-hardening/specs/verification-architecture.md
(REQ-001..REQ-010, PROP-001..PROP-011): every function here is PURE (no I/O, no
sleep, no network) except stabilize_reads, which is an impure DRIVER that calls
an injected read_fn and delegates every comparison to the pure _reads_stable.
"""
import time


def _reads_stable(latest, previous):
    """PURE. Set equality of two href lists (order-independent)."""
    return set(latest) == set(previous)


def stabilize_reads(read_fn, max_reads=3, settle_s=5):
    """Impure DRIVER: collect up to max_reads reads via read_fn, waiting settle_s
    between each, comparing each new read against the immediately preceding one.
    Stops as soon as two consecutive reads match (stable). If max_reads is
    reached with no match, returns inconclusive (stable=False, hrefs=None --
    never the last read used as if trustworthy)."""
    reads = []
    for i in range(max_reads):
        if i > 0:
            time.sleep(settle_s)
        reads.append(read_fn())
        if len(reads) >= 2 and _reads_stable(reads[-1], reads[-2]):
            return {"stable": True, "hrefs": reads[-1]}
    return {"stable": False, "hrefs": None}


def diff_new_href(before_hrefs, after_hrefs):
    """PURE. Returns the first href in after_hrefs not present in before_hrefs, or None."""
    before_set = set(before_hrefs)
    for h in after_hrefs:
        if h not in before_set:
            return h
    return None


def classify_outcome(candidate, reconfirm_hrefs, before_count):
    """PURE. Maps the post-share search+reconfirm result to exactly one of
    "published" / "unverified" / "failed" (REQ-004). The only function allowed
    to produce outcome=="published"."""
    if candidate is None:
        return {"outcome": "failed", "published": False, "post_url": None}
    if reconfirm_hrefs is not None and candidate in reconfirm_hrefs and len(reconfirm_hrefs) == before_count + 1:
        return {"outcome": "published", "published": True, "post_url": candidate}
    return {"outcome": "unverified", "published": False, "post_url": None}


def select_confirmed_href(candidate_hrefs, candidate_page_texts, expected_token):
    """PURE. Given already-fetched candidate hrefs and their already-fetched live
    page innerText, returns the ONE href whose page text CONTAINS expected_token
    as an exact substring, or None if zero or more-than-one contain it."""
    matches = [h for h in candidate_hrefs if expected_token in candidate_page_texts.get(h, "")]
    if len(matches) == 1:
        return matches[0]
    return None
