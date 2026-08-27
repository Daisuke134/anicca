"""Two listings selling the same thing under nearly the same name are one too many."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct  # noqa: E402

FAMILIES = {
    "4357844": "excel_automation",
    "4357869": "excel_automation",
    "91000005": "excel_automation",
    "91000004": "presentation_design",
}
ROWS = [
    {"service_id": "4357844", "title_stem": "請求書作成のExcel自動化要件を整理し"},
    {"service_id": "4357869", "title_stem": "請求書作成のExcel自動化仕様を整理し"},
    {"service_id": "91000005", "title_stem": "Excel作業の自動化を設計から支援し"},
    {"service_id": "91000004", "title_stem": "請求書作成のExcel自動化要件を整理し"},
]


def test_the_two_listings_one_word_apart_are_reported():
    pairs = storefront_direct._near_duplicate_listings(ROWS, FAMILIES)
    assert [pair["service_ids"] for pair in pairs] == [["4357844", "4357869"]]
    assert pairs[0]["title_similarity"] >= 0.9


def test_a_different_offer_in_the_same_family_is_left_alone():
    pairs = storefront_direct._near_duplicate_listings(ROWS, FAMILIES)
    assert all("91000005" not in pair["service_ids"] for pair in pairs)


def test_an_identical_title_in_another_family_is_not_a_duplicate():
    pairs = storefront_direct._near_duplicate_listings(ROWS, FAMILIES)
    assert all("91000004" not in pair["service_ids"] for pair in pairs)


def test_a_listing_whose_title_could_not_be_read_is_not_compared():
    rows = [{"service_id": "4357844", "title_stem": None},
            {"service_id": "4357869", "title_stem": "請求書作成のExcel自動化仕様を整理し"}]
    assert storefront_direct._near_duplicate_listings(rows, FAMILIES) == []


def test_a_pair_stays_a_pair_after_one_of_them_is_reworded():
    """Improving one listing pushed the titles apart and the pair stopped being reported."""
    reworded = [
        {"service_id": "4357844", "title_stem": "請求書の転記・集計をExcelマクロで自動化し"},
        {"service_id": "4357869", "title_stem": "請求書作成のExcel自動化仕様を整理し"},
    ]
    assert storefront_direct._near_duplicate_listings(reworded, FAMILIES) == []


def test_a_withdrawn_listing_is_never_deleted_as_litter(tmp_path):
    """4356229 is a draft because the platform withdrew it, not because a publication failed."""
    import json as _json

    ledger = tmp_path / "new-listing-drafts.jsonl"
    ledger.write_text(_json.dumps({
        "draft_service_id": "4356229", "status": "published", "public_effect": 1,
    }) + "\n", encoding="utf-8")
    drafts = ["4356229", "4356299", "4357788"]

    assert storefront_direct._deletable_drafts(ledger, drafts) == ["4356299", "4357788"]
    assert storefront_direct._deletable_drafts(tmp_path / "absent.jsonl", drafts) == sorted(drafts)


def test_latest_unpublished_candidate_per_family_is_not_deleted_as_litter(tmp_path):
    import json as _json

    ledger = tmp_path / "new-listing-drafts.jsonl"
    ledger.write_text("\n".join(_json.dumps(row) for row in [
        {"draft_service_id": "4371756", "status": "draft_created",
         "capability_family": "ai-automation-builder", "public_effect": 0},
        {"draft_service_id": "4371796", "status": "draft_created",
         "capability_family": "ai-automation-builder", "public_effect": 0},
    ]) + "\n", encoding="utf-8")

    assert storefront_direct._deletable_drafts(
        ledger, ["4371756", "4371796"],
    ) == ["4371756"]
