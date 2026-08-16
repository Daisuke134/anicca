from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


snapshot = load("application_snapshot")


def detail(**overrides):
    value = {
        "request_id": "5214262",
        "canonical_url": "https://coconala.com/requests/5214262",
        "title": "記事作成",
        "category": "記事・Webコンテンツ作成",
        "visible_text": "募集内容\n本文\n応募者一覧\n競合A\n2026/08/16 03:13",
        "accepting_applications": True,
        "budget_min_jpy": 1500,
        "budget_max_jpy": 1500,
        "applicants_count": 1,
        "contracted_count": 0,
        "observed_at": "2026-08-16T10:00:00Z",
        "applicants": [
            {
                "user_id": "5453515",
                "name": "競合A",
                "applied_at": "2026/08/16 03:13",
                "profile_url": "https://coconala.com/users/5453515",
                "rating": 4.9,
                "sales_count": 2,
                "public_services": ["Qualtricsアンケートのカスタマイズします"],
                "profile_summary": "JavaScriptカスタマイズを担当",
            }
        ],
    }
    value.update(overrides)
    return value


def test_application_snapshot_captures_public_applicants():
    normalized = snapshot._normalise_detail(detail())

    assert normalized["applicants"] == detail()["applicants"]
    assert normalized["applicants_count"] == 1


def test_unobservable_competitor_terms_are_never_inferred():
    normalized = snapshot._normalise_detail(detail())

    assert "price_jpy" not in normalized["applicants"][0]
    assert "proposal_text" not in normalized["applicants"][0]
    assert "delivery_days" not in normalized["applicants"][0]


def test_competitor_profile_identity_is_strict():
    bad = detail()
    bad["applicants"][0]["profile_url"] = "https://example.com/users/5453515"

    with pytest.raises(snapshot.SnapshotContractError, match="applicant_profile_url_invalid"):
        snapshot._normalise_detail(bad)
