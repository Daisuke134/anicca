from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reconciler = load("kpi_reconciler")
kpi_contract = load("kpi_contract")


def earning(room: str, receipt: str, jpy: int = 1000) -> dict:
    return {
        "ts": "2026/08/15 10:00",
        "status": "検収完了",
        "talkroom_id": room,
        "requestId": room,
        "idem_key": receipt,
        "jpy": jpy,
        "evidence": "https://coconala.com/mypage/revenue",
    }


def applied(request: str, pass_id: str = "pass-1", **changes) -> dict:
    row = {
        "status": "applied", "requestId": request, "pass_id": pass_id,
        "submit_verified": True, "applied_page_verified": True,
        "ts": "2026-08-15T09:00:00+09:00",
    }
    row.update(changes)
    return row


def test_exact_apply_storefront_and_unknown_preserve_count_and_net():
    report = reconciler.reconcile_rows(
        earnings=[
            earning("room-apply", "receipt-apply", 3000),
            earning("room-store", "receipt-store", 5000),
            earning("room-unknown", "receipt-unknown", 7000),
        ],
        identities=[
            {"talkroom_id": "room-apply", "request_id": "job-1"},
            {
                "talkroom_id": "room-store",
                "service_id": "service-1",
                "service_version_hash": "b" * 64,
            },
        ],
        applications=[applied("job-1")],
        source_sha256="a" * 64,
    )

    assert report["totals"] == {
        "storefront": {"count": 1, "net_jpy": 5000},
        "apply": {"count": 1, "net_jpy": 3000},
        "unknown": {"count": 1, "net_jpy": 7000},
        "all": {"count": 3, "net_jpy": 15000},
    }
    assert report["conserved"] is True
    assert [event["acquisition_lane"] for event in report["events"]] == [
        "apply", "storefront", "unknown"
    ]
    for event in report["events"]:
        kpi_contract.validate_kpi_record(event)


def test_apply_uses_an_exact_application_receipt_identity():
    report = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")],
        [{"talkroom_id": "room-1", "request_id": "job-1"}],
        [applied("job-1")],
        source_sha256="a" * 64,
    )
    identity = report["events"][0]["identity"]
    assert identity["opportunity_id"] == "job-1"
    assert identity["application_id"] == "gig:application:pass-1:job-1"
    assert identity["talkroom_id"] == "room-1"
    assert identity["payment_receipt_id"] == "receipt-1"


def test_collection_observation_time_is_distinct_from_settlement_time():
    row = earning("room-1", "receipt-1")
    row["payout_state_observed_at"] = 1786838400
    event_row = reconciler.reconcile_rows(
        [row], [], [], source_sha256="a" * 64
    )["events"][0]
    assert event_row["occurred_at"] == "2026-08-15T10:00:00+09:00"
    assert event_row["observed_at"] != event_row["occurred_at"]


def test_explicit_falsy_observation_time_cannot_fallback_to_occurrence():
    row = earning("room-1", "receipt-1")
    row["observed_at"] = 0
    with pytest.raises(reconciler.ReconciliationError, match="observed before occurrence"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


def test_direct_offer_without_service_identity_stays_unknown():
    report = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")], [], [], source_sha256="a" * 64
    )
    event = report["events"][0]
    assert event["acquisition_lane"] == "unknown"
    assert event["identity"]["service_id"] is None
    assert "no exact acquisition edge" in event["unknown_reason"]


def test_request_edge_without_application_receipt_stays_unknown():
    report = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")],
        [{"talkroom_id": "room-1", "request_id": "job-1"}],
        [],
        source_sha256="a" * 64,
    )
    assert report["events"][0]["acquisition_lane"] == "unknown"
    assert report["events"][0]["unknown_reason"] == (
        "request edge has no application receipt"
    )


def test_conflicting_exact_edges_stay_unknown_instead_of_double_counting():
    report = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")],
        [
            {"talkroom_id": "room-1", "request_id": "job-1"},
            {
                "talkroom_id": "room-1",
                "service_id": "service-1",
                "service_version_hash": "b" * 64,
            },
        ],
        [applied("job-1")],
        source_sha256="a" * 64,
    )
    assert report["events"][0]["acquisition_lane"] == "unknown"
    assert report["totals"]["all"] == {"count": 1, "net_jpy": 1000}


@pytest.mark.parametrize("changes", [
    {"submit_verified": False},
    {"applied_page_verified": False},
    {"pass_id": ""},
    {"action": "click"},
    {"ts": "bad-time"},
])
def test_unverified_application_fact_stays_unknown(changes: dict):
    report = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")],
        [{"talkroom_id": "room-1", "request_id": "job-1"}],
        [applied("job-1", **changes)],
        source_sha256="a" * 64,
    )
    assert report["events"][0]["acquisition_lane"] == "unknown"


@pytest.mark.parametrize("edges", [
    [
        {"talkroom_id": "room-1", "request_id": "job-1"},
        {"talkroom_id": "room-1", "request_id": "job-2"},
    ],
    [
        {"talkroom_id": "room-1", "request_id": "job-1"},
        {"talkroom_id": "room-1", "service_id": "service-1",
         "service_version_hash": "b" * 64},
    ],
    [
        {"talkroom_id": "room-1", "service_id": "service-1",
         "service_version_hash": "b" * 64},
        {"talkroom_id": "room-1", "request_id": "unverified-job"},
    ],
    [
        {"talkroom_id": "room-1", "request_id": "job-1"},
        {"talkroom_id": "room-2", "request_id": "job-1"},
    ],
])
def test_multiple_or_cross_lane_exact_edges_stay_unknown(edges: list[dict]):
    report = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")], edges, [applied("job-1")],
        source_sha256="a" * 64,
    )
    assert report["events"][0]["acquisition_lane"] == "unknown"
    assert "conflict" in report["events"][0]["unknown_reason"]


def test_conflicting_identity_or_application_aliases_stay_unknown():
    identity_conflict = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")],
        [{"talkroom_id": "room-1", "request_id": "job-1",
          "opportunity_id": "job-2"}],
        [applied("job-1")], source_sha256="a" * 64,
    )
    application_conflict = reconciler.reconcile_rows(
        [earning("room-1", "receipt-1")],
        [{"talkroom_id": "room-1", "request_id": "job-1"}],
        [applied("job-1", request_id="job-2")], source_sha256="a" * 64,
    )
    assert identity_conflict["events"][0]["acquisition_lane"] == "unknown"
    assert application_conflict["events"][0]["acquisition_lane"] == "unknown"


def test_conflicting_payment_talkroom_aliases_fail_closed():
    row = earning("room-1", "receipt-1")
    row["requestId"] = "room-2"
    with pytest.raises(reconciler.ReconciliationError, match="talkroom aliases conflict"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


@pytest.mark.parametrize("field", ["talkroom_id", "idem_key"])
def test_padded_payment_identity_fails_closed(field: str):
    row = earning("room-1", "receipt-1")
    row[field] = f" {row[field]}"
    with pytest.raises(reconciler.ReconciliationError, match="whitespace"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


@pytest.mark.parametrize("missing", ["receipt", "room"])
def test_missing_exact_payment_identity_fails_closed(missing: str):
    row = earning("room-1", "receipt-1")
    if missing == "receipt":
        row["idem_key"] = ""
    else:
        row["talkroom_id"] = ""
        row["requestId"] = ""
    with pytest.raises(reconciler.ReconciliationError):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


def test_duplicate_payment_receipt_fails_closed():
    row = earning("room-1", "receipt-1")
    with pytest.raises(reconciler.ReconciliationError, match="duplicate payment receipt"):
        reconciler.reconcile_rows([row, dict(row)], [], [], source_sha256="a" * 64)


def test_non_settled_or_unproven_rows_do_not_enter_accounting():
    pending = earning("room-1", "receipt-1")
    pending["status"] = "進行中"
    no_evidence = earning("room-2", "receipt-2")
    no_evidence["evidence"] = ""
    zero = earning("room-3", "receipt-3", 0)
    negative = earning("room-4", "receipt-4", -1)
    report = reconciler.reconcile_rows(
        [pending, no_evidence, zero, negative], [], [], source_sha256="a" * 64
    )
    assert report["events"] == []
    assert report["totals"]["all"] == {"count": 0, "net_jpy": 0}


@pytest.mark.parametrize("amount", [True, "1000", None])
def test_proven_settlement_with_malformed_amount_fails_closed(amount):
    row = earning("room-1", "receipt-1")
    row["jpy"] = amount
    with pytest.raises(reconciler.ReconciliationError, match="settlement JPY"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_proven_settlement_with_nonfinite_amount_fails_closed(amount):
    row = earning("room-1", "receipt-1")
    row["jpy"] = amount
    with pytest.raises(reconciler.ReconciliationError, match="settlement JPY"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


@pytest.mark.parametrize("evidence", [True, ["proof"], {"path": "proof"}])
def test_non_string_evidence_fails_closed(evidence):
    row = earning("room-1", "receipt-1")
    row["evidence"] = evidence
    with pytest.raises(reconciler.ReconciliationError, match="evidence"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


def test_padded_evidence_fails_closed():
    row = earning("room-1", "receipt-1")
    row["evidence"] = " proof"
    with pytest.raises(reconciler.ReconciliationError, match="evidence"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


def test_unsafe_integer_jpy_fails_closed():
    row = earning("room-1", "receipt-1", 9007199254740992)
    with pytest.raises(reconciler.ReconciliationError, match="safe integer"):
        reconciler.reconcile_rows([row], [], [], source_sha256="a" * 64)


def test_state_projection_records_each_input_offset_and_hash(tmp_path: Path):
    rows = {
        "earnings.jsonl": [earning("room-1", "receipt-1")],
        "identity_chain.jsonl": [],
        "applied.jsonl": [],
    }
    expected = {}
    for name, values in rows.items():
        content = "".join(json.dumps(value) + "\n" for value in values).encode()
        (tmp_path / name).write_bytes(content)
        expected[name] = {
            "row_offset": len(values),
            "content_sha256": hashlib.sha256(content).hexdigest(),
        }
    assert reconciler.reconcile_state(tmp_path)["inputs"] == expected


def test_malformed_jsonl_fails_closed(tmp_path: Path):
    (tmp_path / "earnings.jsonl").write_text("{torn\n", encoding="utf-8")
    with pytest.raises(reconciler.ReconciliationError, match="malformed earnings.jsonl"):
        reconciler.reconcile_state(tmp_path)


def test_nonstandard_json_constant_fails_closed(tmp_path: Path):
    (tmp_path / "earnings.jsonl").write_text('{"jpy":NaN}\n', encoding="utf-8")
    with pytest.raises(reconciler.ReconciliationError, match="malformed earnings.jsonl"):
        reconciler.reconcile_state(tmp_path)
