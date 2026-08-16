"""CREATE gates learned from live wakes: grammatical titles and one listing per demand.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_create_gates.py
"""
import json
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


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
