"""The code-owned post-submit readback must reconcile Coconala with the ledger."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
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
        "https://coconala.com/requests/91000030",
        "https://coconala.com/job_matching/requests/91000032",
        "https://coconala.com/requests/91000030?ref=applied",
        "https://example.com/requests/999",
    ]
    assert MODULE.extract_request_ids(hrefs) == ["91000030", "91000032"]


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
        "hidden_request_id": "91000030",
        "hrefs": ["https://coconala.com/requests/91000030"],
        "body": "Miffy_nailsの投稿内容 (No.91000030)",
    }) == "91000030"
    assert MODULE.extract_request_id({
        "hidden_request_id": None,
        "hrefs": ["https://coconala.com/job_matching/requests/91000032"],
        "body": "投稿内容",
    }) == "91000032"
    assert MODULE.extract_request_id({
        "hidden_request_id": None,
        "hrefs": [],
        "body": "投稿内容 (No.91000040)",
    }) == "91000040"


def test_parse_offer_fields_uses_seller_owned_card_labels():
    assert MODULE._parse_offer_fields(
        "提案額：21,000円 納品予定日： 2026/08/12"
    ) == {"price_jpy": 21000, "deliver_date": "2026-08-12"}


def test_reconcile_replaces_stale_offer_values_with_live_card_values():
    rows = [{
        "pass_id": "p1",
        "requestId": "91000021",
        "status": "reconcile_pending",
        "price_jpy": 100000,
        "deliver_date": "2026-08-09",
    }]
    reconciled, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"91000021"},
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785250000,
        observations=[{
            "request_id": "91000021",
            "title": "案件タイトル",
            "price_jpy": 21000,
            "deliver_date": "2026-08-12",
        }],
    )
    assert stats["verified"] == 1
    assert reconciled[0]["price_jpy"] == 21000
    assert reconciled[0]["deliver_date"] == "2026-08-12"
    assert reconciled[0]["delivery_date"] == "2026-08-12"


def test_reconcile_marks_only_current_pass_rows_seen_on_applied_page():
    rows = [
        {"pass_id": "p1", "requestId": "91000030", "status": "applied"},
        {"pass_id": "p1", "requestId": "91000032", "status": "applied"},
        {"pass_id": "old", "requestId": "91000030", "status": "applied"},
    ]
    reconciled, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"91000030"},
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785250000,
    )
    assert reconciled[0]["submit_verified"] is True
    assert reconciled[0]["applied_page_verified"] is True
    assert reconciled[0]["applied_page_evidence"] == "/evidence/code-applied-readback.json"
    assert "applied_page_verified" not in reconciled[1]
    assert "applied_page_verified" not in reconciled[2]
    assert stats == {
        "current_pass": 2,
        "verified": 1,
        "missing": 1,
        "unresolved": 0,
    }


def test_reconcile_promotes_intent_candidate_and_enriches_live_title():
    rows = [{
        "pass_id": "p1",
        "requestId": "91000021",
        "status": "reconcile_pending",
        "title": None,
        "recorded_by": "application_report_intent_recovery",
    }]
    reconciled, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"91000021"},
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785250000,
        observations=[{
            "request_id": "91000021",
            "bucket": "single",
            "offer_url": "https://coconala.com/mypage/offers/92000007",
            "title": "AIツール活用のWebサイト制作・運用サポート担当者募集",
        }],
    )
    assert stats["verified"] == 1
    assert reconciled[0]["status"] == "applied"
    assert reconciled[0]["title"] == (
        "AIツール活用のWebサイト制作・運用サポート担当者募集"
    )
    assert reconciled[0]["offer_url"].endswith("/92000007")


def test_readback_route_is_the_authenticated_applied_offer_list():
    assert MODULE.APPLIED_OFFERS_URL == (
        "https://coconala.com/mypage/job_matching/applied/offers"
    )
    assert MODULE.RETAINER_APPLIED_URL == (
        "https://coconala.com/mypage/job_matching/applied/"
        "outsource_applications"
    )


def _fixture(path: Path, request_ids, offers=None) -> Path:
    """A code-owned observation of the canonical applied-offers page."""
    path.write_text(
        json.dumps(
            {
                "source": "code_owned_cdp_readback",
                "url": MODULE.APPLIED_OFFERS_URL,
                "urls": [MODULE.APPLIED_OFFERS_URL],
                "title": "応募・スカウト管理 | ココナラ",
                "observed": True,
                "not_found": False,
                "request_ids": [str(value) for value in request_ids],
                "offers": list(offers or []),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _ledger(path: Path, rows) -> Path:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _run_readback(tmp_path: Path, fixture: Path, ledger: Path, pass_id="p1"):
    output = tmp_path / "code-applied-readback.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fixture",
            str(fixture),
            "--pass-id",
            pass_id,
            "--ledger",
            str(ledger),
            "--output",
            str(output),
            "--screenshot",
            str(tmp_path / "shot.png"),
        ],
        capture_output=True,
        text=True,
    )
    return proc, output


def _rows(ledger: Path):
    return {
        str(row["requestId"]): row
        for row in (
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


# --- "could not read" is not "did not apply" -------------------------------
#
# `application_report.recover_from_intents` deliberately writes rows that do not
# claim the external effect succeeded (submit_verified=False,
# status=reconcile_pending).  A pre-click intent is the crash-safe marker written
# by cdp_nav_snapshot before an irreversible click whose ACK may be lost, so its
# absence from the applied page is an ANSWER the readback obtained, not a failure
# to obtain one.


def test_unverified_intent_candidate_absent_from_applied_page_is_unresolved_not_missing():
    rows = [{
        "pass_id": "p1",
        "requestId": "91000025",
        "status": "reconcile_pending",
        "recorded_by": "application_report_intent_recovery",
        "submit_verified": False,
        "applied_page_verified": False,
    }]
    reconciled, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids=set(),
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785421900,
    )
    assert stats["missing"] == 0
    assert stats["unresolved"] == 1
    assert reconciled[0]["status"] == "reconcile_pending"
    assert reconciled[0]["submit_verified"] is False
    assert reconciled[0]["applied_page_verified"] is False
    assert reconciled[0]["applied_page_absent_at"] == 1785421900
    assert reconciled[0]["applied_page_absent_checks"] == 1


def test_a_claimed_submitted_application_absent_from_applied_page_still_fails():
    """The three-way gate keeps full strength for rows that claim a submit."""
    rows = [
        {
            "pass_id": "p1",
            "requestId": "91000042",
            "status": "applied",
            "submit_verified": True,
        },
        {"pass_id": "p1", "requestId": "91000043", "status": "applied"},
    ]
    _, stats = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids=set(),
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785421900,
    )
    assert stats["missing"] == 2
    assert stats["unresolved"] == 0


def test_absent_candidate_is_never_promoted_to_verified():
    rows = [{
        "pass_id": "p1",
        "requestId": "91000025",
        "status": "reconcile_pending",
        "submit_verified": False,
    }]
    reconciled, _ = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"91000058"},
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785421900,
    )
    assert reconciled[0].get("applied_page_verified") is False
    assert reconciled[0].get("submit_verified") is False
    assert reconciled[0].get("status") == "reconcile_pending"


def test_an_unresolved_candidate_does_not_fail_the_step(tmp_path):
    ledger = _ledger(tmp_path / "applied.jsonl", [
        {
            "pass_id": "p1",
            "requestId": "91000024",
            "status": "reconcile_pending",
            "recorded_by": "application_report_intent_recovery",
            "submit_verified": False,
            "applied_page_verified": False,
        },
        {
            "pass_id": "p1",
            "requestId": "91000025",
            "status": "reconcile_pending",
            "recorded_by": "application_report_intent_recovery",
            "submit_verified": False,
            "applied_page_verified": False,
        },
    ])
    fixture = _fixture(tmp_path / "fixture.json", ["91000024"])
    proc, output = _run_readback(tmp_path, fixture, ledger)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    written = _rows(ledger)
    # The observed application keeps its proof even though a sibling is unresolved.
    assert written["91000024"]["applied_page_verified"] is True
    assert written["91000024"]["status"] == "applied"
    assert written["91000025"]["applied_page_verified"] is False
    assert written["91000025"]["status"] == "reconcile_pending"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["unresolved_count"] == 1
    assert payload["applied_page_absent_request_ids"] == ["91000025"]


def test_verified_proof_is_persisted_even_when_a_claimed_row_is_missing(tmp_path):
    ledger = _ledger(tmp_path / "applied.jsonl", [
        {"pass_id": "p1", "requestId": "91000024", "status": "applied"},
        {
            "pass_id": "p1",
            "requestId": "91000025",
            "status": "applied",
            "submit_verified": True,
        },
    ])
    fixture = _fixture(tmp_path / "fixture.json", ["91000024"])
    proc, _ = _run_readback(tmp_path, fixture, ledger)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    written = _rows(ledger)
    assert written["91000024"]["applied_page_verified"] is True
    assert written["91000025"].get("applied_page_verified") is not True


def test_an_unreadable_applied_page_is_not_reported_as_a_missing_application(tmp_path):
    ledger = _ledger(tmp_path / "applied.jsonl", [
        {"pass_id": "p1", "requestId": "91000025", "status": "applied"},
    ])
    before = ledger.read_text(encoding="utf-8")
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps({"source": "code_owned_cdp_readback", "observed": False}),
        encoding="utf-8",
    )
    proc, _ = _run_readback(tmp_path, fixture, ledger)
    assert proc.returncode == MODULE.EXIT_UNREADABLE
    assert json.loads(proc.stdout.splitlines()[-1])["unreadable"] is True
    # A read that never happened may not rewrite the canonical ledger.
    assert ledger.read_text(encoding="utf-8") == before


def test_bounded_retry_rereads_the_applied_page_before_calling_an_id_absent():
    pages = [
        {"observed": True, "request_ids": ["91000024"]},
        {"observed": True, "request_ids": ["91000024", "91000025"]},
    ]
    slept: list[float] = []
    captured, attempts = MODULE.capture_with_retry(
        lambda: pages.pop(0),
        expected_ids={"91000024", "91000025"},
        attempts=3,
        backoff_seconds=2.0,
        sleeper=slept.append,
    )
    assert attempts == 2
    assert captured["request_ids"] == ["91000024", "91000025"]
    assert slept == [2.0]


def test_bounded_retry_stops_at_the_attempt_ceiling_with_growing_backoff():
    calls = {"n": 0}

    def capture():
        calls["n"] += 1
        return {"observed": True, "request_ids": []}

    slept: list[float] = []
    _, attempts = MODULE.capture_with_retry(
        capture,
        expected_ids={"91000025"},
        attempts=3,
        backoff_seconds=2.0,
        sleeper=slept.append,
    )
    assert attempts == 3
    assert calls["n"] == 3
    assert slept == [2.0, 4.0]


def test_the_readback_can_never_drive_an_irreversible_marketplace_action():
    """The verifier reads. Every duplicate-application risk lives in the submitter."""
    source = SCRIPT.read_text(encoding="utf-8")
    for verb in (
        "Input.dispatchMouseEvent",
        "Input.dispatchKeyEvent",
        "Input.insertText",
        "submit-application",
        "open-application",
    ):
        assert verb not in source, verb


def test_no_absent_row_is_ever_marked_verified_whatever_it_claimed():
    """The one invariant a duplicate submit would need broken."""
    rows = [
        {"pass_id": "p1", "requestId": "91000042", "status": "applied",
         "submit_verified": True},
        {"pass_id": "p1", "requestId": "91000043", "status": "reconcile_pending",
         "submit_verified": False},
        {"pass_id": "p1", "requestId": "91000044"},
    ]
    reconciled, _ = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids=set(),
        evidence_path="/evidence/code-applied-readback.json",
        observed_at=1785421900,
    )
    for row in reconciled:
        assert row.get("applied_page_verified") is not True
        assert "applied_page_verified_at" not in row


def test_gig_pass_reports_an_unreadable_applied_page_under_its_own_reason():
    """The pass must not brand a browser/read outage as a failed application."""
    source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")
    assert "b2_applied_page_readback_unreadable" in source
    assert f'readback_rc" -eq {MODULE.EXIT_UNREADABLE}' in source
    # Losing the readback lease means the page was never read, not that a submit
    # went missing.
    assert f"readback_rc={MODULE.EXIT_UNREADABLE}" in source


def test_torn_historical_ledger_line_is_preserved_while_current_row_is_verified(tmp_path):
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text(
        "{broken historical row\n"
        '{"pass_id":"p1","requestId":"91000030","status":"applied"}\n',
        encoding="utf-8",
    )
    rows = MODULE._read_ledger(ledger)
    assert rows[0] == {"_unparsed": "{broken historical row"}
    reconciled, _ = MODULE.reconcile_rows(
        rows,
        pass_id="p1",
        observed_ids={"91000030"},
        evidence_path="/evidence/readback.json",
        observed_at=1785250000,
    )
    MODULE._write_ledger(ledger, reconciled)
    written = ledger.read_text(encoding="utf-8").splitlines()
    assert written[0] == "{broken historical row"
    assert '"applied_page_verified": true' in written[1]
