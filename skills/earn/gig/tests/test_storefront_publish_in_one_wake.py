"""A draft nobody can reach must not spend the wake's one effect.

The one-effect fence exists to bound what the market sees in a single wake. Creating a
blank draft and filling it are both invisible to buyers -- only publication is an effect
the market can observe. Counting the draft stages meant a wake spent its whole budget
creating a page nobody could reach, then needed two more wakes to fill and publish it, and
each of those wakes had to re-roll a fresh proposal past every content guard. Two filled
drafts sat unpublished on the account while this was true.

The fences that stop a *duplicate* publication are untouched and must stay.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] / "scripts" / "storefront_direct.py").read_text(
    encoding="utf-8")


def _publication_guard() -> str:
    start = SOURCE.index("publication_guard = (")
    return SOURCE[start:start + 900]


def test_a_draft_stage_no_longer_blocks_publication():
    guard = _publication_guard()
    assert "if create_effect_this_wake" not in guard
    assert "if draft_effect_this_wake" not in guard


@pytest.mark.parametrize("fence", [
    "already_public",
    "platform_withdrew_listing",
    "duplicate_listing_title",
    "catalog_capacity_exhausted",
    "existing_listing_effect_open",
])
def test_every_duplicate_publication_fence_survives(fence):
    assert fence in _publication_guard()


def test_a_retire_this_wake_still_blocks_publication():
    # Retiring is buyer-visible, so it really does spend the wake's effect.
    assert "effect_already_this_wake" in _publication_guard()
    assert "retire_attempted_this_wake" in _publication_guard()


def test_the_wake_effect_counts_only_what_buyers_can_see():
    line = re.search(r"draft_effect_this_wake = [^\n]*", SOURCE).group(0)
    assert "public_effect" in line
    assert '"effect"' not in line, (
        "a filled but unpublished draft is not an effect the market can see")


def test_filling_the_draft_is_no_longer_skipped_after_a_create():
    # `prepare_draft` used to be skipped whenever a blank draft was created in the same wake.
    start = SOURCE.index("storefront_draft.prepare_draft(")
    block = SOURCE[start:start + 500]
    assert "not create_effect_this_wake" not in block


def test_the_create_record_no_longer_overwrites_what_filling_reported():
    start = SOURCE.index("if create_effect_this_wake:")
    block = SOURCE[start:start + 400]
    # `**draft_result` must come last so the real stage wins over the create placeholder.
    assert block.index("**draft_result") > block.index('"status": "draft_created"')
