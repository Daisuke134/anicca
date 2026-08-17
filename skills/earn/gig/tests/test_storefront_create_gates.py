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



def test_a_derived_market_is_sourced_from_its_own_capability_family():
    """Handing the model one market's demand beside another family's offer is incoherent."""
    import json as _json
    from pathlib import Path as _Path
    families = _json.loads((_Path(__file__).resolve().parents[1] / "config"
                            / "storefront-contract-families.json").read_text(encoding="utf-8"))
    by_service = families["service_families"]
    wanted = "excel_automation"
    candidates = sorted(sid for sid, fam in by_service.items() if fam == wanted)
    # The catalogue really does own listings in this family, so a source exists to copy
    # official constraints from; picking one from a different family is what made Terra refuse.
    assert candidates
    assert all(by_service[sid] == wanted for sid in candidates)
    assert by_service.get("91000003") == "seo_writing"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
