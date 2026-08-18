"""A listing must stop advertising an offer its capability family no longer promises."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct  # noqa: E402

MACRO_FAMILY = {"inclusions": ["マクロの作成"], "deliverables": ["動作するExcelマクロ（VBA）ファイル"]}
DOCUMENT_FAMILY = {"inclusions": ["設計書の作成"], "deliverables": ["自動化設計書"]}


def test_a_listing_with_no_body_history_is_due(tmp_path):
    assert storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "4244910", "excel_automation", MACRO_FAMILY)


def test_a_body_change_carrying_the_digest_closes_it(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "4244910", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "4244910", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "4244910", "excel_automation", MACRO_FAMILY) is None


def test_changing_the_family_again_makes_it_due_again(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "4244910", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "4244910", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "4244910", "excel_automation", DOCUMENT_FAMILY)


def test_another_listings_rewrite_does_not_close_this_one(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "4244910", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "4244910", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "4313386", "excel_automation", MACRO_FAMILY)


def test_a_title_change_does_not_close_a_body_promise(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "4244910", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "4244910", "status": "accepted", "effect": 1,
        "changed_field": "title", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "4244910", "excel_automation", MACRO_FAMILY)


def test_the_excel_family_now_ships_a_working_macro():
    families = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "storefront-contract-families.json")
        .read_text(encoding="utf-8"))["families"]
    deliverables = families["excel_automation"]["deliverables"]
    assert any("マクロ" in item for item in deliverables)
    assert not any("設計書" in item for item in deliverables)


def test_an_offer_the_listings_already_advertise_is_not_a_change(tmp_path):
    digest = storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "4244910", "excel_automation", MACRO_FAMILY)
    assert storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "4244910", "excel_automation", MACRO_FAMILY,
        already_advertised={digest}) is None


def test_a_genuinely_new_offer_is_still_due_with_a_baseline(tmp_path):
    other = storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "4244910", "excel_automation", DOCUMENT_FAMILY)
    assert storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "4244910", "excel_automation", MACRO_FAMILY,
        already_advertised={other})


def test_the_title_is_still_due_after_the_body_is_rewritten(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "4357844", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "4357844", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "4357844", "excel_automation", MACRO_FAMILY, field="body") is None
    assert storefront_direct._offer_refresh_due(
        effects, "4357844", "excel_automation", MACRO_FAMILY, field="title") == digest


def test_the_catchphrase_follows_the_title(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "4357844", "excel_automation", MACRO_FAMILY)
    effects.write_text("".join(json.dumps({
        "service_id": "4357844", "status": "accepted", "effect": 1,
        "changed_field": field, "offer_digest": digest,
    }) + "\n" for field in ("body", "title")), encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "4357844", "excel_automation", MACRO_FAMILY, field="title") is None
    assert storefront_direct._offer_refresh_due(
        effects, "4357844", "excel_automation", MACRO_FAMILY, field="catchphrase") == digest


def test_the_catchphrase_is_a_field_the_loop_may_change():
    assert "catchphrase" in storefront_direct.MUTATION_FIELDS
    assert "catchphrase" in storefront_direct.GENERATED_MUTATION_FIELDS


def test_every_text_field_set_knows_the_catchphrase():
    """A field missing from one of these sets has its sealed contract silently ignored.

    The catchphrase reached the field set, the form mapping and the readback mapping but not
    the executor branch, so a valid contract fell through to the general judge and the wake
    answered about a different listing.
    """
    import re
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "storefront_direct.py").read_text(
        encoding="utf-8")
    sets = re.findall(r'\{"[A-Za-z_", ]*"title"[A-Za-z_", ]*\}', source)
    assert sets, "no field set found; this test guards the wrong thing"
    assert [item for item in sets if "catchphrase" not in item] == []
