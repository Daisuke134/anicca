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
        tmp_path / "effects.jsonl", "91000005", "excel_automation", MACRO_FAMILY)


def test_a_body_change_carrying_the_digest_closes_it(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "91000005", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "91000005", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "91000005", "excel_automation", MACRO_FAMILY) is None


def test_changing_the_family_again_makes_it_due_again(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "91000005", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "91000005", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "91000005", "excel_automation", DOCUMENT_FAMILY)


def test_another_listings_rewrite_does_not_close_this_one(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "91000005", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "91000005", "status": "accepted", "effect": 1,
        "changed_field": "body", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "91000002", "excel_automation", MACRO_FAMILY)


def test_a_title_change_does_not_close_a_body_promise(tmp_path):
    effects = tmp_path / "effects.jsonl"
    digest = storefront_direct._offer_refresh_due(effects, "91000005", "excel_automation", MACRO_FAMILY)
    effects.write_text(json.dumps({
        "service_id": "91000005", "status": "accepted", "effect": 1,
        "changed_field": "title", "offer_digest": digest,
    }) + "\n", encoding="utf-8")
    assert storefront_direct._offer_refresh_due(
        effects, "91000005", "excel_automation", MACRO_FAMILY)


def test_an_offer_the_listings_already_advertise_is_not_a_change(tmp_path):
    digest = storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "91000005", "excel_automation", MACRO_FAMILY)
    assert storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "91000005", "excel_automation", MACRO_FAMILY,
        already_advertised={digest}) is None


def test_a_genuinely_new_offer_is_still_due_with_a_baseline(tmp_path):
    other = storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "91000005", "excel_automation", DOCUMENT_FAMILY)
    assert storefront_direct._offer_refresh_due(
        tmp_path / "effects.jsonl", "91000005", "excel_automation", MACRO_FAMILY,
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


def test_a_refresh_does_not_replay_a_contract_already_published():
    """A committed seed whose exact value is live is spent; the refresh must ask for new copy."""
    contract = {"service_id": "91000005", "changed_field": "body",
                "proposed_value": "旧本文", "contract_sha256": "c" * 64}
    rendered = {("91000005", "body"): contract}
    spent = {("91000005", "body", json.dumps("旧本文", ensure_ascii=False, sort_keys=True))}

    assert storefront_direct._refresh_contract(rendered, spent, "91000005", "body") is None
    assert storefront_direct._refresh_contract(rendered, set(), "91000005", "body") is contract
    assert storefront_direct._refresh_contract(rendered, set(), "91000005", "title") is None


def test_a_seed_the_listing_has_moved_past_is_skipped_not_raised(monkeypatch, tmp_path):
    """Improving a listing invalidates its committed seed; that is finished work, not a fault."""
    spec = tmp_path / "seed.json"
    spec.write_text(json.dumps({
        "version": 1, "platform": "coconala", "service_id": "91000005",
        "capability_family": "excel_automation",
        "changed_field": "body", "form_field": "data[Service][head]",
        "before_value": "古い本文", "rollback_value": "古い本文", "proposed_value": "新しい本文",
        "official_readback": {"public_body_sha256": "d" * 64},
        "success_metric": "inquiries", "observation_window_days": 14,
        "evidence": ["official:seller-form:91000005"],
    }, ensure_ascii=False), encoding="utf-8")
    contracts = [{"service_id": "91000005", "service_version_sha256": "a" * 64,
                  "public_url": "https://coconala.com/services/91000005"}]
    snapshot = {
        "url": "https://coconala.com/mypage/services/91000005",
        "fields": [{"name": "data[Service][head]", "value": "すでに書き換えた本文"}],
    }

    assert storefront_direct._render_text_mutation(
        spec, contracts, snapshot, {"91000005": "excel_automation"}) is None

    wrong_page = {**snapshot, "url": "https://coconala.com/mypage/services/9999999"}
    try:
        storefront_direct._render_text_mutation(
            spec, contracts, wrong_page, {"91000005": "excel_automation"})
    except RuntimeError as error:
        assert "storefront_text_mutation_before_not_current" in str(error)
    else:
        raise AssertionError("a snapshot of the wrong listing was accepted")


def test_the_listing_people_look_at_and_never_contact_comes_first(tmp_path):
    """474 views produced one inquiry, so the break is at views to inquiry."""
    analytics = tmp_path / "analytics.jsonl"
    analytics.write_text("".join(json.dumps({
        "service_id": service_id, "metrics": {"views": {"value": views}},
    }) + "\n" for service_id, views in (("A", 91), ("B", 64), ("C", 10), ("D", 73))), encoding="utf-8")
    funnel = tmp_path / "funnel-events.jsonl"
    funnel.write_text(json.dumps({"event_kind": "inquiry", "service_id": "D"}) + "\n", encoding="utf-8")

    ranked = storefront_direct._traffic_without_inquiries(analytics, funnel)

    assert ranked == ["A", "B"], "most viewed first, contacted and low-traffic listings excluded"
    assert storefront_direct._traffic_without_inquiries(
        tmp_path / "absent.jsonl", funnel) == []
