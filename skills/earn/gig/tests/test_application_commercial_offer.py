from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("application_parent", SCRIPTS / "application_parent.py")
assert SPEC and SPEC.loader
application_parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_parent)


def test_price_is_owned_by_code_when_competitor_terms_are_private() -> None:
    detail = {"budget_min_jpy": 50_000, "budget_max_jpy": 100_000}

    assert application_parent.commercial_offer_price(detail, planner_price_jpy=88_000) == 99_000


def test_price_respects_a_narrow_official_budget() -> None:
    detail = {"budget_min_jpy": 100_000, "budget_max_jpy": 100_000}

    assert application_parent.commercial_offer_price(detail, planner_price_jpy=88_000) == 100_000


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
