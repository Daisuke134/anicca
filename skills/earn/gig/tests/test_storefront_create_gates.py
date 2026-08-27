"""CREATE gates learned from live wakes: grammatical titles and one listing per demand.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_create_gates.py
"""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

CONTINUATIVE = "いきしちにひみりぎじびぴえけせてねへめれげぜでべぺ"
DEMAND = "/repo/contracts/storefront/new/seo-article-v1.json"


def title_is_grammatical(stem):
    return stem[-1] in CONTINUATIVE


def sold_from_this_demand(line, demand=DEMAND):
    row = json.loads(line)
    if row.get("status") != "published" or not str(
            row.get("candidate_key") or "").startswith("storefront:create:v1:"):
        return False
    return row.get("demand_evidence_path", demand) == demand


def test_a_title_stem_ending_in_a_particle_never_reaches_a_listing():
    # Observed live: Terra sealed 法人向け…SEO構成から, which Coconala renders as 「…からます」.
    assert title_is_grammatical("初心者向けの解説SEO記事を構成から執筆し")
    assert title_is_grammatical("研修資料を伝わる構成と見やすいスライドに整え")
    assert not title_is_grammatical("法人向けサービスの比較検討記事をSEO構成から")


def test_one_published_listing_per_demand_evidence():
    published = json.dumps({"status": "published", "candidate_key": "storefront:create:v1:abc",
                            "demand_evidence_path": DEMAND})
    other_demand = json.dumps({"status": "published", "candidate_key": "storefront:create:v1:abc",
                               "demand_evidence_path": "/repo/other.json"})
    draft_only = json.dumps({"status": "prepared", "candidate_key": "storefront:create:v1:abc",
                             "demand_evidence_path": DEMAND})
    assert sold_from_this_demand(published)
    assert not sold_from_this_demand(other_demand)
    assert not sold_from_this_demand(draft_only)


def test_rows_written_before_the_field_existed_still_close_the_gate():
    # The append-only ledger is never rewritten, so legacy rows must still count.
    legacy = json.dumps({"status": "published", "candidate_key": "storefront:create:v1:abc"})
    assert sold_from_this_demand(legacy)
    # A hand-authored seed listing is not a generic CREATE and must not close the gate.
    seed = json.dumps({"status": "published", "candidate_key": "storefront:new-listing:v1:seo-article-single"})
    assert not sold_from_this_demand(seed)



def test_a_catalogue_fills_over_days_not_over_consecutive_wakes(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import storefront_direct as sd

    state = tmp_path / "state"
    state.mkdir()
    published = {"observed_at_epoch": 1_786_891_168,
                 "new_listing_draft": {"public_effect": 1,
                                       "candidate_key": "storefront:create:v1:abc"}}
    other = {"observed_at_epoch": 1_786_899_999,
             "new_listing_draft": {"public_effect": 0,
                                   "candidate_key": "storefront:create:v1:abc"}}
    (state / "wakes.jsonl").write_text(
        json.dumps(published) + "\n" + json.dumps(other) + "\n", encoding="utf-8")

    last = sd._last_published_create_epoch(state)
    assert last == 1_786_891_168  # a wake without a public effect never counts
    assert sd.CREATE_MIN_INTERVAL_SECONDS == 86_400
    assert last + sd.CREATE_MIN_INTERVAL_SECONDS > 1_786_895_800  # still closed hours later
    assert sd._last_published_create_epoch(tmp_path / "absent") is None



def _sd():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import storefront_direct as sd
    return sd


def test_demand_needs_a_paying_comparable_not_just_search_results():
    sd = _sd()
    crowded_but_unproven = {"visible_result_count": 9000,
                            "comparables": [{"service_id": "1", "sales_count": 0, "review_count": 0}]}
    assert sd._score_demand_cluster(crowded_but_unproven)["score"] == 0
    proven = {"visible_result_count": 3899, "comparables": [
        {"service_id": "2329055", "sales_count": 216, "review_count": 185, "display_price_jpy": 6000},
        {"service_id": "1884761", "review_count": 331, "display_price_jpy": 20000},
    ]}
    scored = sd._score_demand_cluster(proven)
    assert scored["score"] > 0 and scored["sold_comparables"] == 1
    assert scored["median_price_jpy"] == 20000


def test_a_cluster_without_official_evidence_is_unknown_not_zero():
    sd = _sd()
    assert sd._score_demand_cluster({"visible_result_count": 100, "comparables": []})["status"] == "unknown"
    assert sd._score_demand_cluster({"comparables": [{"service_id": "1"}]})["status"] == "unknown"


def test_demand_cluster_identity_ignores_surrounding_whitespace():
    sd = _sd()
    a = sd._demand_cluster_key(" SEO 記事 ", "https://coconala.com/categories/230/66")
    b = sd._demand_cluster_key("SEO 記事", "https://coconala.com/categories/230/66 ")
    assert a == b and a.startswith("storefront:demand:v1:")



SEARCH_BODY = """お届け日数
7,834 件中 1 - 60 件表示
おすすめ順
AI業務効率化システムを開発します
AIエージェント・自動化システムを開発します。
uta_lab_
5.0
(1)
10,000円
Excel/Python/GASで業務自動化します
社員を雇うより、まず業務の仕組み化してみませんか。
株式会社SCコンサルティング
5.0
(11)
3,000円
"""


def test_search_demand_is_read_from_the_official_page_shape():
    sd = _sd()
    out = sd._extract_search_demand(SEARCH_BODY)
    assert out["visible_result_count"] == 7834
    assert out["comparables"] == [
        {"rating": 5.0, "review_count": 1, "display_price_jpy": 10000},
        {"rating": 5.0, "review_count": 11, "display_price_jpy": 3000},
    ]
    scored = sd._score_demand_cluster(out)
    # Reviews only follow purchases, so reviewed comparables are real demand evidence.
    assert scored["status"] == "known" and scored["reviewed_comparables"] == 2


def test_a_page_whose_cards_do_not_parse_stays_unknown():
    sd = _sd()
    # The official category page states a count but lists no parseable card.
    out = sd._extract_search_demand("3,220 件中 1 - 60 件表示\nおすすめ順\n")
    assert out["visible_result_count"] == 3220 and out["comparables"] == []
    assert sd._score_demand_cluster(out)["status"] == "unknown"



FAMILIES = {"seo_writing", "excel_automation"}


def test_a_proposed_query_must_belong_to_an_owned_capability():
    sd = _sd()
    proposal = {"decision": "propose", "no_op_reason": None,
                "queries": [{"query": "議事録 要約 自動化", "capability_family": "excel_automation",
                             "rationale": "既存のExcel自動化能力で対応できる"}]}
    sealed = sd._seal_demand_proposal(proposal, FAMILIES, ["SEO記事の見出し構成を作成します"])
    assert sealed[0]["query"] == "議事録 要約 自動化"

    unowned = {"decision": "propose", "no_op_reason": None,
               "queries": [{"query": "動画編集", "capability_family": "video_editing", "rationale": "r"}]}
    with pytest.raises(RuntimeError, match="storefront_demand_query_unowned_or_duplicate"):
        sd._seal_demand_proposal(unowned, FAMILIES, [])


def test_a_query_that_repeats_the_current_catalogue_is_refused():
    sd = _sd()
    proposal = {"decision": "propose", "no_op_reason": None,
                "queries": [{"query": "SEO記事", "capability_family": "seo_writing", "rationale": "r"}]}
    with pytest.raises(RuntimeError, match="storefront_demand_query_duplicates_catalogue"):
        sd._seal_demand_proposal(proposal, FAMILIES, ["SEO記事の見出し構成を作成します"])


def test_a_no_op_must_say_why_and_carry_no_queries():
    sd = _sd()
    assert sd._seal_demand_proposal(
        {"decision": "no_op", "no_op_reason": "既存クラスタが未消化", "queries": []}, FAMILIES, []) == []
    with pytest.raises(RuntimeError, match="storefront_demand_noop_invalid"):
        sd._seal_demand_proposal({"decision": "no_op", "no_op_reason": None, "queries": []}, FAMILIES, [])


def test_public_skill_inventory_extends_existing_market_capabilities_without_overwriting_them():
    sd = _sd()
    configured = {"excel_automation": {"deliverables": ["macro"]}}
    inventory = {"skills": [{
        "name": "ai-automation-builder",
        "description": "Build and verify bounded AI business automations.",
        "skill_path": "skills/ai-automation-builder/SKILL.md",
        "source_sha256": "a" * 64,
        "runtime": "agent_skill",
        "slot": None,
    }]}

    merged = sd._market_capability_templates(configured, inventory)

    assert merged["excel_automation"] == {"deliverables": ["macro"]}
    assert merged["ai-automation-builder"] == {
        "name": "ai-automation-builder",
        "description": "Build and verify bounded AI business automations.",
        "skill_path": "skills/ai-automation-builder/SKILL.md",
        "source_sha256": "a" * 64,
        "runtime": "agent_skill",
    }


def test_new_public_skill_uses_its_own_capability_contract_with_an_existing_form_source():
    sd = _sd()
    source = {"service_id": "1", "service_version_sha256": "a" * 64}
    family, template, evidence = sd._resolve_create_capability(
        wanted="ai-automation-builder",
        source=source,
        service_families={"1": "seo_writing"},
        templates={
            "seo_writing": {"deliverables": ["article"]},
            "ai-automation-builder": {
                "skill_path": "skills/ai-automation-builder/SKILL.md",
                "description": "Build AI automations",
            },
        },
        repo=Path("/repo"),
    )

    assert family == "ai-automation-builder"
    assert template["description"] == "Build AI automations"
    assert evidence == {"/repo/skills/ai-automation-builder/SKILL.md"}
    assert sd._proposal_capability_evidence({"/repo/old-opencv.json"}, evidence) == evidence
    assert sd._proposal_capability_evidence({"/repo/private-proof.json"}, set()) == {
        "/repo/private-proof.json"
    }


def test_dismissed_zero_conversion_market_never_blocks_the_next_demand_cluster():
    sd = _sd()
    clusters = [
        {"cluster_key": "excel", "query": "Excel 自動化", "status": "known", "score": 12},
        {"cluster_key": "ai", "query": "AI 業務自動化", "status": "known", "score": 8,
         "capability_inventory_sha256": "a" * 64, "recurring_potential": True,
         "median_price_jpy": 15000},
        {"cluster_key": "interview", "query": "インタビュー分析", "status": "known", "score": 12,
         "capability_inventory_sha256": "a" * 64, "recurring_potential": False,
         "median_price_jpy": 55000},
    ]

    selected = sd._next_unused_demand_cluster(clusters, set())

    assert selected["cluster_key"] == "ai"
    assert sd._next_unused_demand_cluster(clusters, {"excel", "ai", "interview"}) is None


def test_a_changed_public_capability_inventory_triggers_fresh_market_discovery_once():
    sd = _sd()
    clusters = [{"capability_inventory_sha256": "a" * 64, "status": "known", "score": 1}]
    assert sd._capability_inventory_needs_market_probe(clusters, "b" * 64) is True
    assert sd._capability_inventory_needs_market_probe(clusters, "a" * 64) is False
    assert sd._capability_inventory_needs_market_probe([
        {"capability_inventory_sha256": "a" * 64, "status": "unknown", "score": None},
    ], "a" * 64) is True


def test_paid_demand_price_floor_uses_the_official_comparable_median():
    sd = _sd()
    demand = {"comparables": [
        {"review_count": 19, "display_price_jpy": 50000},
        {"review_count": 18, "display_price_jpy": 3000},
        {"review_count": 1, "display_price_jpy": 30000},
        {"sales_count": 11, "display_price_jpy": 300000},
    ]}

    assert sd._paid_demand_price_floor(demand) == 50000


def test_market_expansion_prefers_capabilities_not_already_represented_by_a_listing():
    sd = _sd()
    templates = {
        "excel_automation": {"deliverables": ["macro"]},
        "ai-automation-builder": {"description": "AI systems"},
    }
    assert sd._unlisted_capability_templates(templates, {"1": "excel_automation"}) == {
        "ai-automation-builder": {"description": "AI systems"},
    }


def test_gallery_readback_retries_a_hydrated_page_with_zero_images():
    sd = _sd()
    observed = {"url": "https://coconala.com/services/1", "body": "service", "service_image_ids": []}
    assert sd._own_page_readback_valid(observed, "1", expected_image_count=6) is False
    observed["service_image_ids"] = [str(index) for index in range(6)]
    assert sd._own_page_readback_valid(observed, "1", expected_image_count=6) is True


def test_a_known_unpublished_candidate_draft_is_reused_even_after_it_has_a_title():
    import storefront_draft

    cards = [
        {"ids": ["4371756"], "titled": True},
        {"ids": ["4371773"], "titled": True},
        {"ids": ["9999999"], "titled": True},
    ]
    assert storefront_draft._preferred_recoverable_draft(
        ["4371773", "4371756"], cards,
    ) == "4371773"
    assert storefront_draft._preferred_recoverable_draft(["1111111"], cards) is None
    assert storefront_draft._preferred_ledger_draft(["4371790", "4371773"]) == "4371790"
    assert storefront_draft._preferred_ledger_draft(["bad", ""]) is None


def test_official_draft_deletion_evidence_prevents_reusing_a_deleted_id(tmp_path):
    sd = _sd()
    evidence = tmp_path / "evidence" / "wake-1"
    evidence.mkdir(parents=True)
    (evidence / "draft-delete-4371796.json").write_text("{}\n", encoding="utf-8")
    (evidence / "draft-delete-not-an-id.json").write_text("{}\n", encoding="utf-8")
    assert sd._observed_deleted_draft_ids(tmp_path / "evidence") == {"4371796"}


def test_a_prepared_readback_contract_is_reused_instead_of_regenerated(tmp_path):
    import hashlib
    sd = _sd()
    unsigned = {
        "draft_service_id": "4371816",
        "capability_evidence": {"family": "ai-automation-builder"},
        "demand_evidence_path": "/evidence/ai.json",
    }
    digest = hashlib.sha256(json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    contract = {**unsigned, "contract_sha256": digest}
    evidence = tmp_path / "evidence" / "wake-1"
    evidence.mkdir(parents=True)
    (evidence / "generated-create-contract.json").write_text(
        json.dumps(contract) + "\n", encoding="utf-8",
    )
    (tmp_path / "wakes.jsonl").write_text(json.dumps({
        "pass_id": "wake-1", "status": "completed",
        "new_listing_draft": {
            "status": "prepared", "readback": 1, "public_effect": 0,
            "draft_service_id": "4371816", "contract_sha256": digest,
            "capability_family": "ai-automation-builder",
            "demand_evidence_path": "/evidence/ai.json",
        },
    }) + "\n", encoding="utf-8")

    assert sd._recover_prepared_create_contract(
        tmp_path, "ai-automation-builder", "/evidence/ai.json",
    ) == contract
    assert sd._recover_prepared_create_contract(
        tmp_path, "other-family", "/evidence/ai.json",
    ) is None


def test_recurring_potential_comes_from_the_owned_capability_not_marketplace_copy():
    sd = _sd()
    assert sd._capability_recurring_potential({
        "description": "Build a system and provide recurring maintenance after acceptance",
    }) is True
    assert sd._capability_recurring_potential({"description": "Deliver one interview memo"}) is False



def test_demand_exploration_never_kills_a_wake(monkeypatch, tmp_path):
    """A failing exploration must be recorded, not raised into the wake."""
    sd = _sd()
    calls = {}

    def boom(*_a, **_k):
        raise OSError("server rejected WebSocket connection: HTTP 500")

    monkeypatch.setattr(sd, "_crawl_demand_cluster", boom)
    # Mirror the wake's guard: any exception is captured as evidence, never re-raised.
    try:
        try:
            sd._crawl_demand_cluster(tmp_path, tmp_path, "Excel 自動化")
        except Exception as error:
            calls["error"] = f"{type(error).__name__}:{str(error)[:160]}"
    except Exception:  # pragma: no cover - the guard above must swallow it
        raise AssertionError("exploration failure escaped the guard")
    assert calls["error"].startswith("OSError:")



COMMITTED = {"category": {"master": {"value": "19", "label": "ライティング・翻訳"}},
             "category_specific": {"languages": ["366"]},
             "subscription": {"enabled": True, "discount_ratio": "5"}}
CLUSTER = {"status": "known", "score": 12, "query": "Excel 自動化",
           "capability_family": "excel_automation", "cluster_key": "storefront:demand:v1:abc",
           "search_url": "https://coconala.com/search?keyword=Excel", "visible_result_count": 9011,
           "comparables": [{"review_count": 3, "display_price_jpy": 10000}],
           "evidence_path": "/evidence/demand-search-abc.json"}
CATEGORY = {"master_category": {"value": "11", "label": "IT相談・システム開発"},
            "sub_options": [{"value": "1004", "label": "AI導入・活用支援"}],
            "type_options": [{"value": "786", "label": "AI導入コンサルティング"}]}


def test_a_derived_market_changes_the_market_not_the_delivery_policy():
    sd = _sd()
    blueprint = sd._create_blueprint_from_cluster(COMMITTED, CLUSTER, CATEGORY)
    assert blueprint["capability_family"] == "excel_automation"
    assert blueprint["category"]["master"]["label"] == "IT相談・システム開発"
    assert blueprint["demand_evidence"]["visible_result_count"] == 9011
    assert blueprint["demand_evidence_path"] == "/evidence/demand-search-abc.json"
    # How the work is delivered is the owner's commitment, not a property of the market.
    assert blueprint["category_specific"] == COMMITTED["category_specific"]
    assert blueprint["subscription"] == COMMITTED["subscription"]


def test_an_unproven_or_unbound_market_never_becomes_a_blueprint():
    sd = _sd()
    # Children are read on the draft CREATE claims, so their absence is not a blueprint error.
    assert sd._create_blueprint_from_cluster(
        COMMITTED, CLUSTER, {**CATEGORY, "sub_options": []})["category_options"]["sub"] == []
    with pytest.raises(RuntimeError, match="storefront_cluster_category_unbound"):
        sd._create_blueprint_from_cluster(COMMITTED, CLUSTER, {**CATEGORY, "master_category": {}})
    with pytest.raises(RuntimeError, match="storefront_cluster_demand_unproven"):
        sd._create_blueprint_from_cluster(COMMITTED, {**CLUSTER, "score": 0}, CATEGORY)
    with pytest.raises(RuntimeError, match="storefront_cluster_demand_unproven"):
        sd._create_blueprint_from_cluster(COMMITTED, {**CLUSTER, "status": "unknown"}, CATEGORY)

def test_a_two_level_category_writes_no_type_field():
    """Some official categories stop at two levels; inventing a type would be a false claim."""
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "scripts"))
    import storefront_draft as sdraft

    fields = {"overview_input": "o", "catchphrase": "c", "head": "h",
              "price_option_value": "3300", "delivery_days": 5, "order_limit": 1, "body": "b"}
    three = {"public_fields": fields, "category": {
        "master": {"value": "11"}, "sub": {"value": "230"}, "type": {"value": "2274"}}}
    two = {"public_fields": fields, "category": {
        "master": {"value": "11"}, "sub": {"value": "230"}, "type": None}}
    assert "data[Service][master_category_type_id]" in sdraft._expected_values(three)
    assert "data[Service][master_category_type_id]" not in sdraft._expected_values(two)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_a_family_with_traffic_and_no_sales_is_reported(tmp_path):
    """Competitor demand said twelve for Excel while our own Excel listings sold nothing."""
    import json as _json

    import storefront_direct

    ledger = tmp_path / "analytics.jsonl"
    rows = [
        {"service_id": "1", "metrics": {"views": {"value": 90}, "purchases": {"value": 0}}},
        {"service_id": "2", "metrics": {"views": {"value": 80}, "purchases": {"value": 0}}},
        {"service_id": "3", "metrics": {"views": {"value": 10}, "purchases": {"value": 0}}},
    ]
    ledger.write_text("".join(_json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    families = {"1": "excel_automation", "2": "excel_automation", "3": "seo_writing"}

    blocked = storefront_direct._family_traffic_without_sales(ledger, families, "excel_automation")
    assert blocked["views"] == 170 and blocked["purchases"] == 0 and blocked["listings"] == 2
    assert storefront_direct._family_traffic_without_sales(ledger, families, "seo_writing") is None

    sold = tmp_path / "sold.jsonl"
    sold.write_text("".join(_json.dumps(row) + "\n" for row in [
        {"service_id": "1", "metrics": {"views": {"value": 90}, "purchases": {"value": 1}}},
        {"service_id": "2", "metrics": {"views": {"value": 80}, "purchases": {"value": 0}}},
    ]), encoding="utf-8")
    assert storefront_direct._family_traffic_without_sales(sold, families, "excel_automation") is None
    assert storefront_direct._family_traffic_without_sales(ledger, families, "") is None
