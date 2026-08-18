"""A listing the platform took down must not be published again by the loop."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct  # noqa: E402


def _ledger(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "new-listing-drafts.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


PUBLISHED = {"draft_service_id": "91000003", "status": "published", "public_effect": 1}


def test_a_listing_we_published_that_is_gone_counts_as_withdrawn(tmp_path):
    assert storefront_direct._platform_withdrew_listing(
        _ledger(tmp_path, [PUBLISHED]), "91000003", is_public=False) is True


def test_a_listing_still_public_is_not_withdrawn(tmp_path):
    assert storefront_direct._platform_withdrew_listing(
        _ledger(tmp_path, [PUBLISHED]), "91000003", is_public=True) is False


def test_a_draft_never_published_is_not_withdrawn(tmp_path):
    rows = [{"draft_service_id": "91000003", "status": "prepared", "public_effect": 0}]
    assert storefront_direct._platform_withdrew_listing(
        _ledger(tmp_path, rows), "91000003", is_public=False) is False


def test_another_listing_being_published_says_nothing_about_this_one(tmp_path):
    assert storefront_direct._platform_withdrew_listing(
        _ledger(tmp_path, [PUBLISHED]), "4357844", is_public=False) is False


def test_no_ledger_yet_is_not_a_withdrawal(tmp_path):
    assert storefront_direct._platform_withdrew_listing(
        tmp_path / "absent.jsonl", "91000003", is_public=False) is False


def test_a_corrupt_ledger_fails_closed(tmp_path):
    path = tmp_path / "new-listing-drafts.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="new_listing_draft_ledger_invalid"):
        storefront_direct._platform_withdrew_listing(path, "91000003", is_public=False)
