from __future__ import annotations

import importlib.util
from pathlib import Path
import inspect
import json
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("application_parent", SCRIPTS / "application_parent.py")
assert SPEC and SPEC.loader
application_parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_parent)


def test_budget_discount_v1_price_bands() -> None:
    cases = ((5_000, 4_000), (50_000, 45_000), (80_000, 70_000))

    for budget_max, expected in cases:
        assert application_parent._target_offer_price(
            budget_max=budget_max,
            official_min=1_000,
            official_max=budget_max,
            profitability_floor=1_000,
            category_contract_median=None,
        ) == expected


def test_price_respects_a_narrow_official_budget() -> None:
    detail = {"budget_min_jpy": 100_000, "budget_max_jpy": 100_000}

    assert application_parent.commercial_offer_price(detail, planner_price_jpy=88_000) == 100_000


def test_target_offer_price_respects_all_money_bounds() -> None:
    assert application_parent._target_offer_price(
        budget_max=50_000,
        official_min=48_000,
        official_max=50_000,
        profitability_floor=47_000,
        category_contract_median=None,
    ) == 48_000


def test_unprofitable_budget_is_not_applied() -> None:
    assert application_parent._target_offer_price(
        budget_max=50_000,
        official_min=1_000,
        official_max=50_000,
        profitability_floor=60_000,
        category_contract_median=None,
    ) is None


def test_quote_request_uses_only_verified_category_median() -> None:
    assert application_parent._target_offer_price(
        budget_max=None,
        official_min=1_000,
        official_max=100_000,
        profitability_floor=20_000,
        category_contract_median=65_000,
    ) == 65_000
    assert application_parent._target_offer_price(
        budget_max=None,
        official_min=1_000,
        official_max=100_000,
        profitability_floor=20_000,
        category_contract_median=None,
    ) is None


def test_quote_request_reads_verified_category_contract_median(tmp_path, monkeypatch) -> None:
    ledger = tmp_path / "applied.jsonl"
    projects = tmp_path / "projects"
    projects.mkdir()
    for request_id, category, price in (
        ("100", "翻訳", 40_000),
        ("101", "翻訳", 60_000),
        ("102", "Web制作", 200_000),
    ):
        (projects / request_id).mkdir()
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "request_id": request_id, "category": category, "price_jpy": price,
            }, ensure_ascii=False) + "\n")
    monkeypatch.setenv("GIG_APPLIED_LEDGER", str(ledger))
    monkeypatch.setenv("GIG_PROJECTS_ROOT", str(projects))

    assert application_parent.commercial_offer_price(
        {"category": "翻訳", "budget_min_jpy": None, "budget_max_jpy": None},
        planner_price_jpy=999_000,
    ) == 50_000


def test_application_does_not_navigate_competitor_profiles() -> None:
    source = inspect.getsource(application_parent.CdpParentEffects._detail_async)

    assert "coconala.com/users/" not in source


def test_confirmed_application_records_pricing_version() -> None:
    row = application_parent._application_row(
        {
            "request_id": "123",
            "category": "IT・プログラミング",
            "title": "自動化",
            "canonical_url": "https://coconala.com/requests/123",
        },
        {"price_jpy": 45_000, "deliver_date": "2026-08-20"},
    )

    assert row["pricing_basis"] == "budget_discount_v1_10pct"


def test_proposal_opens_with_commitment_and_has_no_pre_contract_question() -> None:
    proposal = application_parent.commercial_proposal_text(
        "詳細をご共有いただけますか？要件に沿ってLINE Botを構築します。",
        price_jpy=99_000,
        deliver_date="2026-08-20",
    )

    assert proposal.startswith("対応可能です。")
    assert "？" not in proposal and "?" not in proposal
    assert "99,000円" in proposal
    assert "2026-08-20" in proposal
    assert "契約範囲内でご納得いただけるまで" in proposal
