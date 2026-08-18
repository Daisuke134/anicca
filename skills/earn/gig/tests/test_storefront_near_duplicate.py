"""Two listings selling the same thing under nearly the same name are one too many."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct  # noqa: E402

FAMILIES = {
    "4357844": "excel_automation",
    "4357869": "excel_automation",
    "4244910": "excel_automation",
    "4308502": "presentation_design",
}
ROWS = [
    {"service_id": "4357844", "title_stem": "請求書作成のExcel自動化要件を整理し"},
    {"service_id": "4357869", "title_stem": "請求書作成のExcel自動化仕様を整理し"},
    {"service_id": "4244910", "title_stem": "Excel作業の自動化を設計から支援し"},
    {"service_id": "4308502", "title_stem": "請求書作成のExcel自動化要件を整理し"},
]


def test_the_two_listings_one_word_apart_are_reported():
    pairs = storefront_direct._near_duplicate_listings(ROWS, FAMILIES)
    assert [pair["service_ids"] for pair in pairs] == [["4357844", "4357869"]]
    assert pairs[0]["title_similarity"] >= 0.9


def test_a_different_offer_in_the_same_family_is_left_alone():
    pairs = storefront_direct._near_duplicate_listings(ROWS, FAMILIES)
    assert all("4244910" not in pair["service_ids"] for pair in pairs)


def test_an_identical_title_in_another_family_is_not_a_duplicate():
    pairs = storefront_direct._near_duplicate_listings(ROWS, FAMILIES)
    assert all("4308502" not in pair["service_ids"] for pair in pairs)


def test_a_listing_whose_title_could_not_be_read_is_not_compared():
    rows = [{"service_id": "4357844", "title_stem": None},
            {"service_id": "4357869", "title_stem": "請求書作成のExcel自動化仕様を整理し"}]
    assert storefront_direct._near_duplicate_listings(rows, FAMILIES) == []
