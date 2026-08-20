from __future__ import annotations

import importlib.util
from pathlib import Path
import inspect
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("application_parent", SCRIPTS / "application_parent.py")
assert SPEC and SPEC.loader
application_parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_parent)


def test_commercial_offer_preserves_planner_price() -> None:
    detail = {"budget_min_jpy": 10_000, "budget_max_jpy": 30_000}

    assert application_parent.commercial_offer_price(detail, planner_price_jpy=15_000) == 15_000


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

    assert row["pricing_basis"] == "planner_selected_v1"


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
