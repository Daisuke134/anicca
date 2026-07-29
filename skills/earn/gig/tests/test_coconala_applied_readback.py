"""The code-owned post-submit readback must reconcile Coconala with the ledger."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "coconala_applied_readback.py"
SPEC = importlib.util.spec_from_file_location("coconala_applied_readback", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_extract_request_ids_accepts_both_public_request_routes_and_dedupes():
    hrefs = [
        "https://coconala.com/requests/5176621",
        "https://coconala.com/job_matching/requests/5177000",
        "https://coconala.com/requests/5176621?ref=applied",
        "https://example.com/requests/999",
    ]
    assert MODULE.extract_request_ids(hrefs) == ["5176621", "5177000"]


def test_extract_retainer_ids_accepts_ulid_detail_routes_and_dedupes():
    retainer_id = "01KYKDECET9WAY0CKRBCKH81RC"
    hrefs = [
        f"https://coconala.com/job_matching/outsources/{retainer_id}",
        f"https://coconala.com/job_matching/outsources/{retainer_id}?from=applied",
        "https://example.com/job_matching/outsources/01KYKDECET9WAY0CKRBCKH81RC",
    ]
    assert MODULE.extract_retainer_ids(hrefs) == [retainer_id]


def test_retainer_readback_binds_hidden_listing_ulid_by_unique_exact_title():
    retainer_id = "01KYKDECET9WAY0CKRBCKH81RC"
    cards = [{
        "title": "Meta APIを活用したSaaS開発エンジニア募集",
        "talkroom_url": (
            "https://coconala.com/mypage/job_matching/"
            "job_talkroom/01ABC/talkroom"
        ),
    }]
    matched, observations = MODULE.match_retainer_ids_by_title(
        cards,
        {retainer_id: "Meta APIを活用したSaaS開発エンジニア募集"},
    )
    assert matched == {retainer_id}
    assert observations[0]["request_id"] == retainer_id
    assert observations[0]["identity_binding"] == "exact_title_unique"


def test_retainer_readback_refuses_an_ambiguous_duplicate_title():
    title = "同名案件"
    cards = [
        {"title": title, "talkroom_url": "https://coconala.com/talkroom/1"},
        {"title": title, "talkroom_url": "https://coconala.com/talkroom/2"},
    ]
    matched, observations = MODULE.match_retainer_ids_by_title(
        cards,
        {"01KYKDECET9WAY0CKRBCKH81RC": title},
    )
    assert matched == set()
    assert observations == []


def test_retainer_readback_waits_for_nextjs_cards_after_document_ready():
    retainer_id = "01KYKDECET9WAY0CKRBCKH81RC"
    title = "Meta APIを活用したSaaS開発エンジニア募集"
    pages = [
        {
            "url": MODULE.RETAINER_APPLIED_URL,
            "title": "応募・スカウト管理",
            "hrefs": [],
            "cards": [],
            "body_sample": "応募・スカウト管理",
            "not_found": False,
        },
        {
            "url": MODULE.RETAINER_APPLIED_URL,
            "title": "応募・スカウト管理",
            "hrefs": [],
            "cards": [{
                "title": title,
                "talkroom_url": (
                    "https://coconala.com/mypage/job_matching/"
                    "job_talkroom/01ABC"
                ),
            }],
            "body_sample": f"{title}\n応募済み",
            "not_found": False,
        },
    ]

    async def fake_call(_ws, _method, _params, _call_id):
        return {"result": {"value": json.dumps(pages.pop(0), ensure_ascii=False)}}

    with mock.patch.object(MODULE, "_call", side_effect=fake_call):
        page, next_call_id = asyncio.run(MODULE._wait_for_retainer_page(
            object(),
            10,
            expected_titles={retainer_id: title},
            poll_seconds=0,
            timeout_seconds=1,
        ))

    assert page["cards"][0]["title"] == title
    assert next_call_id == 12


def test_extract_request_id_from_offer_edit_page_uses_canonical_request_identity():
    assert MODULE.extract_request_id({
        "hidden_request_id": "5176621",
        "hrefs": ["https://coconala.com/requests/5176621"],
        "body": "Miffy_nailsの投稿内容 (No.5176621)",
    }) == "5176621"
    assert MODULE.extract_request_id({
        "hidden_request_id": None,
        "hrefs": ["https://coconala.com/job_matching/requests/5177000"],
        "body": "投稿内容",
    }) == "5177000"
    assert MODULE.extract_request_id({
        "hidden_request_id": None,
        "hrefs": [],
        "body": "投稿内容 (No.5178000)",
    }) == "5178000"


def test_reconcile_marks_only_current_pass_rows_seen_on_applied_page():
    rows = [
        {"pass_id": "p1", "requestId": "5176621", "status": "applied"},
        {"pass_id": "p1", "requestId": "5177000", "status": "applied"},
        {"pass_id": "old", "requestId": "5176621", "status": "applied"},
    ]
    reconciled, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"5176621"},
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785250000,
    )
    assert reconciled[0]["submit_verified"] is True
    assert reconciled[0]["applied_page_verified"] is True
    assert reconciled[0]["applied_page_evidence"] == "/evidence/code-applied-readback.json"
    assert "applied_page_verified" not in reconciled[1]
    assert "applied_page_verified" not in reconciled[2]
    assert stats == {"current_pass": 2, "verified": 1, "missing": 1}


def test_reconcile_promotes_intent_candidate_and_enriches_live_title():
    rows = [{
        "pass_id": "p1",
        "requestId": "5170842",
        "status": "reconcile_pending",
        "title": None,
        "recorded_by": "application_report_intent_recovery",
    }]
    reconciled, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"5170842"},
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785250000,
        observations=[{
            "request_id": "5170842",
            "bucket": "single",
            "offer_url": "https://coconala.com/mypage/offers/6274001",
            "title": "AIツール活用のWebサイト制作・運用サポート担当者募集",
        }],
    )
    assert stats["verified"] == 1
    assert reconciled[0]["status"] == "applied"
    assert reconciled[0]["title"] == (
        "AIツール活用のWebサイト制作・運用サポート担当者募集"
    )
    assert reconciled[0]["offer_url"].endswith("/6274001")


def test_readback_route_is_the_authenticated_applied_offer_list():
    assert MODULE.APPLIED_OFFERS_URL == (
        "https://coconala.com/mypage/job_matching/applied/offers"
    )
    assert MODULE.RETAINER_APPLIED_URL == (
        "https://coconala.com/mypage/job_matching/applied/"
        "outsource_applications"
    )


def test_torn_historical_ledger_line_is_preserved_while_current_row_is_verified(tmp_path):
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text(
        "{broken historical row\n"
        '{"pass_id":"p1","requestId":"5176621","status":"applied"}\n',
        encoding="utf-8",
    )
    rows = MODULE._read_ledger(ledger)
    assert rows[0] == {"_unparsed": "{broken historical row"}
    reconciled, _ = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"5176621"},
        evidence_path="/evidence/readback.json",
        observed_at=1785250000,
    )
    MODULE._write_ledger(ledger, reconciled)
    written = ledger.read_text(encoding="utf-8").splitlines()
    assert written[0] == "{broken historical row"
    assert '"applied_page_verified": true' in written[1]
