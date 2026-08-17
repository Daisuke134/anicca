"""A measurement window must buy evidence; otherwise it must not lock the listing.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_fence.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402

SERVICE_ID = "4244910"


def analytics(tmp_path, views, status="known"):
    path = tmp_path / "analytics.jsonl"
    path.write_text(json.dumps({
        "service_id": SERVICE_ID, "observed_at_epoch": 1_786_000_000,
        "metrics": {"views": {"status": status, "value": views}},
    }) + "\n", encoding="utf-8")
    return path


def test_a_window_that_cannot_reach_the_minimum_is_not_worth_waiting_for(tmp_path):
    # 93 views per 30 days projects to 43 in a 14-day window: far under the 100 minimum.
    result = sd._measurement_feasible(analytics(tmp_path, 93), SERVICE_ID, 14, 100)
    assert result["status"] == "known"
    assert result["projected_window_views"] == 43
    assert result["feasible"] is False
    assert result["basis"] == "rolling_30d_view_rate_projected_onto_window"


def test_a_listing_with_real_traffic_keeps_its_window(tmp_path):
    result = sd._measurement_feasible(analytics(tmp_path, 900), SERVICE_ID, 14, 100)
    assert result["projected_window_views"] == 420 and result["feasible"] is True


def test_missing_or_unknown_official_views_stay_unknown(tmp_path):
    assert sd._measurement_feasible(tmp_path / "absent.jsonl", SERVICE_ID, 14, 100)["status"] == "unknown"
    unknown = sd._measurement_feasible(analytics(tmp_path, 0, status="unavailable"), SERVICE_ID, 14, 100)
    assert unknown["status"] == "unknown" and unknown["reason"] == "no_official_views_for_service"


def test_the_policy_states_the_threshold_it_enforces():
    policy = sd._portfolio_policy(
        Path(__file__).resolve().parents[1] / "config" / "storefront-catalog-scorecard.json")
    assert policy["minimum_views_for_measurement"] == 100
    # Freeing a listing must never be allowed to look like a retirement decision.
    assert policy["short_term_zero_sales_can_retire"] is False



def test_a_stale_hand_authored_contract_is_skipped_not_fatal(tmp_path):
    """One listing moving on must not stop the wake for every other listing."""
    import pytest

    root = tmp_path / "contracts"
    root.mkdir()
    (root / "4313386.json").write_text(json.dumps({
        "version": 1, "platform": "coconala", "service_id": "4313386",
        "public_url": "https://coconala.com/services/4313386",
        "service_version_sha256": "a" * 64,
        "offer": {"base_price_jpy": 6000, "required_inputs": ["x"]},
        "inquiry_playbook": {"answer_patterns": [
            {"intent": "i", "triggers": ["t"], "response": "r"}]},
    }), encoding="utf-8")
    observed = [{"service_id": "4313386",
                 "public_url": "https://coconala.com/services/4313386",
                 "service_version_sha256": "b" * 64, "price_jpy": 6000,
                 "title": "請求書・日報のVBA自動化を支援します", "state": "公開中",
                 "category": "IT・プログラミング", "public_text": "サービス内容"}]

    families = Path(__file__).resolve().parents[1] / "config" / "storefront-contract-families.json"
    loaded = sd._load_listing_contracts(root, observed, families_path=families)
    # The stale hand-authored file is recorded rather than raised...
    assert sd._stale_listing_contracts
    assert sd._stale_listing_contracts[0]["service_id"] == "4313386"
    assert sd._stale_listing_contracts[0]["reason"] == "listing_contract_binding_stale"
    # ...and the listing still gets a contract, derived from its capability family, bound to
    # the version actually observed rather than the one the stale file remembered.
    derived = [row for row in loaded if row["service_id"] == "4313386"]
    assert derived and derived[0]["service_version_sha256"] == "b" * 64


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
