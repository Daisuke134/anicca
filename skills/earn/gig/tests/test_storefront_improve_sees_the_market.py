"""The IMPROVE path must see the same official demand facts the CREATE path already does.

Measured 2026-09-07: `excel_vba_gas_automation` comparables include a listing at 29,000 yen with
464 reviews and one at 3,000 yen with 428 reviews, while this account's three Excel listings sit
at 7,000/6,000/5,000 yen with zero sales. That structured signal (median_price_jpy,
sold_comparables, reviewed_comparables, visible_result_count, per-comparable price/rating/review
counts) reached only `_create_proposal_prompt`. `_proposal_prompt`, which governs every live
IMPROVE mutation, only ever saw raw competitor page bodies it was told never to use for pricing --
so a zero-sale 7,000-yen listing never learned its own family sells at 29,000 yen with hundreds of
reviews. This file pins the fix: a `family_market` reader on the kernel, threaded into both
judgement prompts the same way `prior_rejections` already is.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_improve_sees_the_market.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import storefront_direct as direct  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: the two real measured demand-evidence rows named in the defect report
# ---------------------------------------------------------------------------

EXCEL_FAMILY = "excel_vba_gas_automation"
LINE_BOT_FAMILY = "line_bot_dev"


def _excel_row() -> dict:
    return {
        "capability_family": EXCEL_FAMILY,
        "query": "Excel VBA 自動化",
        "rationale": "model's own reasoning for choosing this query",
        "evidence_path": "/tmp/demand-search-excel.json",
        "median_price_jpy": 7500,
        "sold_comparables": 2,
        "reviewed_comparables": 2,
        "visible_result_count": 5000,
        "comparables": [
            {"display_price_jpy": 29000, "rating": 5.0, "review_count": 464,
             "title": "競合seller's own listing title", "url": "https://coconala.com/services/1"},
            {"display_price_jpy": 3000, "rating": 4.9, "review_count": 428,
             "title": "別の競合タイトル", "url": "https://coconala.com/services/2"},
        ],
    }


def _line_bot_row() -> dict:
    return {
        "capability_family": LINE_BOT_FAMILY,
        "query": "LINE bot 開発",
        "rationale": "why this query",
        "evidence_path": "/tmp/demand-search-line-bot.json",
        "median_price_jpy": 35000,
        "sold_comparables": 12,
        "reviewed_comparables": 12,
        "visible_result_count": 1657,
        "comparables": [
            {"display_price_jpy": 20000, "rating": 5.0, "review_count": 10},
            {"display_price_jpy": 80000, "rating": 5.0, "review_count": 3},
        ],
    }


def _ledger(state_dir: Path, rows: list[dict]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "demand-evidence.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8",
    )


def _minimal_proposal_prompt_args(family_market=None, prior_rejections=None):
    hypothesis = {"service_id": "1", "field": "price", "success_metric": "inquiries"}
    source = {"service_id": "1", "service_version_sha256": "a" * 64}
    return direct._proposal_prompt(
        hypothesis, source, {}, EXCEL_FAMILY, {}, {"sources": []}, set(),
        prior_rejections=prior_rejections, family_market=family_market,
    )


# ---------------------------------------------------------------------------
# The kernel alias reads the ledger the same way the create path's demand ledger does
# ---------------------------------------------------------------------------

def test_family_market_alias_reduces_the_ledger_row_to_public_facts_only(tmp_path):
    state = tmp_path / "state"
    _ledger(state, [_excel_row(), _line_bot_row()])
    market = direct._family_market(state, EXCEL_FAMILY)
    assert market == {
        "median_price_jpy": 7500, "sold_comparables": 2, "reviewed_comparables": 2,
        "visible_result_count": 5000, "evidence_path": "/tmp/demand-search-excel.json",
        "comparables": [
            {"display_price_jpy": 29000, "rating": 5.0, "review_count": 464},
            {"display_price_jpy": 3000, "rating": 4.9, "review_count": 428},
        ],
    }
    assert direct._family_market(state, "no_such_family") is None
    assert direct._family_market(tmp_path / "no-such-state", EXCEL_FAMILY) is None


# ---------------------------------------------------------------------------
# (4) CONTEXT_JSON carries family_market when present, and omits the key -- not an empty
#     value -- when it is absent, so an empty market is never confused with none measured.
# ---------------------------------------------------------------------------

def test_improve_prompt_omits_family_market_key_when_absent():
    prompt, _ = _minimal_proposal_prompt_args(family_market=None)
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert "family_market" not in context


def test_improve_prompt_includes_family_market_when_present():
    market = direct._family_market(_ledger_dir_for(_excel_row()), EXCEL_FAMILY)
    prompt, _ = _minimal_proposal_prompt_args(family_market=market)
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert context["family_market"] == market


def _ledger_dir_for(*rows) -> Path:
    import tempfile
    state = Path(tempfile.mkdtemp()) / "state"
    _ledger(state, list(rows))
    return state


# ---------------------------------------------------------------------------
# (5) evidence_path is added to allowed_evidence_refs when a market exists, so a proposal
#     may cite it -- the validator in _seal_generated_proposal only accepts refs from this set.
# ---------------------------------------------------------------------------

def test_evidence_path_is_added_to_allowed_evidence_refs_when_market_exists(tmp_path):
    _ledger(tmp_path, [_excel_row()])
    market = direct._family_market(tmp_path, EXCEL_FAMILY)
    prompt, allowed_refs = _minimal_proposal_prompt_args(family_market=market)
    assert "/tmp/demand-search-excel.json" in allowed_refs
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert "/tmp/demand-search-excel.json" in context["allowed_evidence_refs"]


def test_allowed_evidence_refs_unaffected_when_no_market():
    prompt, allowed_refs = _minimal_proposal_prompt_args(family_market=None)
    assert all("demand-search" not in ref for ref in allowed_refs)


# ---------------------------------------------------------------------------
# (6) The instruction boundary is expression, not knowledge: still forbids copying wording
#     and images, no longer forbids using the observed price/rating/review distribution.
# ---------------------------------------------------------------------------

def test_prompt_forbids_copying_wording_and_images_but_not_using_observed_market_data():
    prompt, _ = _minimal_proposal_prompt_args()
    normalized = " ".join(prompt.split())
    assert "Never copy a competitor's wording, images, review text, claims or results" in normalized
    assert "family_market is public fact about this market and MUST be used" in normalized
    assert "say what the family's median price is" in normalized
    # The old sentence forbade citing a competitor's sales/speed/guarantees alongside wording;
    # it must be gone, not merely supplemented, since it directly contradicted the new MUST.
    assert "never copy their wording, images, reviews, sales, speed, guarantees or results" not in normalized


# ---------------------------------------------------------------------------
# (7) The real measured Excel-family numbers actually reach the built prompt text.
# ---------------------------------------------------------------------------

def test_the_measured_excel_family_price_and_review_count_reach_the_built_prompt(tmp_path):
    _ledger(tmp_path, [_excel_row()])
    market = direct._family_market(tmp_path, EXCEL_FAMILY)
    prompt, _ = _minimal_proposal_prompt_args(family_market=market)
    assert "29000" in prompt
    assert "464" in prompt


# ---------------------------------------------------------------------------
# _judgement_prompt gets the same treatment (the legacy FAQ-only judge path)
# ---------------------------------------------------------------------------

def test_judgement_prompt_omits_family_market_key_when_absent():
    prompt = direct._judgement_prompt({"url": "u", "body": ""}, {"sources": []}, set())
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert "family_market" not in context


def test_judgement_prompt_includes_family_market_when_present(tmp_path):
    _ledger(tmp_path, [_excel_row()])
    market = direct._family_market(tmp_path, EXCEL_FAMILY)
    prompt = direct._judgement_prompt(
        {"url": "u", "body": ""}, {"sources": []}, set(), family_market=market,
    )
    context = json.loads(prompt.split("CONTEXT_JSON=", 1)[1])
    assert context["family_market"] == market
    assert "29000" in prompt


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
