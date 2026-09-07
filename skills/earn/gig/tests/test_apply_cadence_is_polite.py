"""Apply wakes every 30 minutes, not every minute.

Measured 2026-09-07: Coconala refuses every application. The refusal is silent and deliberate --
the `応募する` button fires correctly (`handleOfferClick(){window.open(this.offerUrl,"_blank")}`,
`offerUrl` = `/offers/add/<id>`, the same route the lane uses), a new tab really opens under a user
gesture, and the server redirects it straight back to the request page. No error, no message, the
button left in place. That is the shape of throttling, not of a broken client.

What preceded it: 806 applications cumulative, 26 on 2026-09-02 alone, from a lane waking every
60 seconds. The last successful application is 2026-09-02 15:05.

Thirty minutes costs nothing. Postings stay open for days -- the one measured on 09-07 had 14 days
left -- and 806 applications produced 6 contracts (0.74%), so fit decides outcomes, not speed.

Run: python3 -m pytest skills/earn/gig/tests/test_apply_cadence_is_polite.py
"""

import json
from pathlib import Path

REGISTRY = json.loads((Path(__file__).resolve().parents[4] / "config" / "loop-registry.json")
                      .read_text(encoding="utf-8"))


def _lane(name):
    def find(node):
        if isinstance(node, dict):
            if name in node:
                return node[name]
            for value in node.values():
                found = find(value)
                if found is not None:
                    return found
        return None
    lane = find(REGISTRY)
    assert lane is not None, f"{name} is not in the registry"
    return lane


def test_apply_wakes_every_thirty_minutes():
    assert _lane("hf-gig-apply-direct")["cadence"]["start_interval_seconds"] == 1800


def test_it_is_not_back_to_a_minute():
    """60s is what preceded the refusal; a revert should have to be deliberate."""
    assert _lane("hf-gig-apply-direct")["cadence"]["start_interval_seconds"] >= 900


def test_only_the_applying_lane_was_slowed():
    """Storefront and Paid do not submit applications, so their cadence is not implicated."""
    assert _lane("hf-gig-storefront-direct")["cadence"]["start_interval_seconds"] == 60
    assert _lane("hf-gig-paid-direct")["cadence"]["start_interval_seconds"] == 300
