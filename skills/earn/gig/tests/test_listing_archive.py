#!/usr/bin/env python3
"""Deterministic-parts tests for listing_archive.py (gig-loop spec Task C2).

No network, no browser -- covers only the ledger row shape and idempotent append, the
same split listing_inventory.py's own tests use for its deterministic half.
"""
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import listing_archive as la  # noqa: E402
import listing_ledger  # noqa: E402


def test_archive_row_is_its_own_kind_not_the_publish_taxonomy():
    # Guards the reason this action exists: an archive must not be classified as a
    # publish/create/edit event, or B0's objective math (published_listings /
    # created_listings) would be inflated by a listing being taken DOWN. C3
    # (2026-08-09): it is now its own KIND_ARCHIVED (not the earlier KIND_TOUCHED)
    # because count() needs to tell "was archived" apart from "was merely touched" to
    # net a previously-published id back out of published_listings.
    assert la.ARCHIVE_ACTION in listing_ledger.ACTION_KIND
    assert listing_ledger.classify(la.ARCHIVE_ACTION) == listing_ledger.KIND_ARCHIVED


def test_build_ledger_row_shape():
    row = la.build_ledger_row(
        ts=1786228303, pass_id="c2-delist-1786228303", service_id="94000007",
        title="SNS縦型ショート動画を1本編集します", reason="capability_mismatch_delist",
    )
    assert row["action"] == "shuppin_archived"
    assert row["service_id"] == "94000007"
    assert row["reason"] == "capability_mismatch_delist"
    assert row["url"] == "https://coconala.com/services/94000007"


def test_archive_requires_buyer_visible_marker():
    assert la.ARCHIVED_MARKERS
    assert any(marker in "サービス詳細に受付終了と表示されます" for marker in la.ARCHIVED_MARKERS)
    assert not any(marker in "購入する 受付中" for marker in la.ARCHIVED_MARKERS)


def test_archive_state_accepts_seller_inventory_absence_for_reachable_direct_url():
    # Coconala documents that an archived service's direct URL can remain
    # reachable; absence from the authenticated seller list is authoritative.
    assert la.archive_state_confirmed(confirmation=False, inventory_absent=True)
    assert not la.archive_state_confirmed(confirmation=True, inventory_absent=False)
    assert not la.archive_state_confirmed(confirmation=False, inventory_absent=False)


def test_build_ledger_row_carries_readback_evidence():
    row = la.build_ledger_row(
        ts=1, pass_id="p1", service_id="94000007", title="t",
        reason="capability_mismatch_delist",
        evidence={"public_url": "https://coconala.com/services/94000007", "public_archived": True},
    )
    assert row["evidence"]["public_archived"] is True


def test_append_ledger_row_dedupes_same_pass(tmp_path):
    ledger_path = tmp_path / "shuppin.jsonl"
    row = la.build_ledger_row(
        ts=1, pass_id="p1", service_id="94000007", title="t", reason="capability_mismatch_delist",
    )
    assert la.append_ledger_row(ledger_path, row) is True
    assert la.append_ledger_row(ledger_path, row) is False  # same pass_id+action+service_id
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["service_id"] == "94000007"


def test_append_ledger_row_does_not_count_as_published():
    ledger_path_events = [
        listing_ledger.ListingEvent(
            kind=listing_ledger.classify("shuppin_archived"),
            service_ids=("94000007",), ts=1, raw_action="shuppin_archived",
        ),
    ]
    counts = listing_ledger.count(ledger_path_events)
    assert counts.published_listings == 0
    assert counts.created_listings == 0
    assert counts.known_listings == 1  # still visible, just not counted as productive


def test_archiving_a_previously_published_id_nets_it_back_out():
    # C3 (2026-08-09): the actual drift C1's inventory found -- a listing published then
    # later archived must stop counting as published, or a recycled slot counts forever.
    events = [
        listing_ledger.ListingEvent(
            kind=listing_ledger.classify("shuppin_published"),
            service_ids=("94000007",), ts=1, raw_action="shuppin_published",
        ),
        listing_ledger.ListingEvent(
            kind=listing_ledger.classify("shuppin_archived"),
            service_ids=("94000007",), ts=2, raw_action="shuppin_archived",
        ),
    ]
    counts = listing_ledger.count(events)
    assert counts.published_listings == 0
    assert counts.published_events == 1  # the historical publish row still happened
    assert counts.known_listings == 1


if __name__ == "__main__":
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", __file__, "-q"], check=True)
