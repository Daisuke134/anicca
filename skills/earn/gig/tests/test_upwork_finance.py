from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


GIG = Path(__file__).resolve().parents[1]
SCRIPTS, PROVIDERS = GIG / "scripts", GIG / "scripts" / "providers"
for directory in (SCRIPTS, PROVIDERS):
    sys.path.insert(0, str(directory))

from upwork_finance import FinanceError, list_payments  # noqa: E402


HASH = "a" * 64
WINDOW = {
    "start": "2026-08-01", "end": "2026-08-31", "complete": True,
    "evidence_sha256": HASH,
}
JOIN = {
    "contract-1": {
        "contract_sha256": "b" * 64, "submission_id": "submission-1",
        "delivery_evidence_sha256": "c" * 64, "execution_id": "d" * 64,
        "execution_cost_usd_minor": 500,
    },
}


def _row(transaction_id, kind, amount, *, status="available", related=None):
    return {
        "transaction_id": transaction_id, "related_payment_id": related,
        "contract_id": "contract-1", "milestone_id": "milestone-1",
        "kind": kind, "status": status, "currency": "USD", "amount_minor": amount,
        "occurred_at": "2026-08-23T05:00:00+00:00", "evidence_sha256": HASH,
    }


def _payment(status="available"):
    return [
        _row("payment-1", "payment", 10_000, status=status),
        _row("fee-1", "fee", 1_000, status=status, related="payment-1"),
    ]


@pytest.mark.parametrize("status", ["in_review", "pending", "available"])
def test_unreceived_balances_never_become_verified_revenue(tmp_path, status):
    result = list_payments(
        _payment(status), source_window=WINDOW, accounting_period="2026-08",
        project_evidence=JOIN, claims_path=tmp_path / "claims.jsonl",
    )[0]

    assert result["state"] == status
    assert result["payout_available"] is (status == "available")
    assert result["recognized_revenue_usd_minor"] is None
    assert result["verified_net_usd_minor"] is None


def test_received_payout_joins_contract_delivery_and_actual_cost(tmp_path):
    rows = _payment() + [
        _row("payout-1", "payout", 9_000, status="received", related="payment-1"),
    ]
    result = list_payments(
        rows, source_window=WINDOW, accounting_period="2026-08",
        project_evidence=JOIN, claims_path=tmp_path / "claims.jsonl",
    )[0]

    assert result["provider_transaction_ids"] == ["fee-1", "payment-1", "payout-1"]
    assert result["gross_usd_minor"] == 10_000
    assert result["fee_usd_minor"] == 1_000
    assert result["refund_usd_minor"] == 0
    assert result["chargeback_usd_minor"] == 0
    assert result["recognized_revenue_usd_minor"] == 9_000
    assert result["execution_cost_usd_minor"] == 500
    assert result["verified_net_usd_minor"] == 8_500
    assert result["submission_id"] == "submission-1"


def test_refund_and_chargeback_reduce_received_money(tmp_path):
    rows = _payment() + [
        _row("refund-1", "refund", 2_000, status="completed", related="payment-1"),
        _row("chargeback-1", "chargeback", 1_000, status="completed", related="payment-1"),
        _row("payout-1", "payout", 6_000, status="received", related="payment-1"),
    ]
    result = list_payments(
        rows, source_window=WINDOW, accounting_period="2026-08",
        project_evidence=JOIN, claims_path=tmp_path / "claims.jsonl",
    )[0]

    assert result["refund_usd_minor"] == 2_000
    assert result["chargeback_usd_minor"] == 1_000
    assert result["recognized_revenue_usd_minor"] == 6_000
    assert result["verified_net_usd_minor"] == 5_500


def test_missing_fee_or_project_join_remains_unknown(tmp_path):
    rows = [_row("payment-1", "payment", 10_000)] + [
        _row("payout-1", "payout", 10_000, status="received", related="payment-1"),
    ]
    result = list_payments(
        rows, source_window=WINDOW, accounting_period="2026-08",
        project_evidence={}, claims_path=tmp_path / "claims.jsonl",
    )[0]

    assert result["fee_usd_minor"] is None
    assert result["execution_cost_usd_minor"] is None
    assert result["recognized_revenue_usd_minor"] is None
    assert result["verified_net_usd_minor"] is None


def test_missing_or_incomplete_source_window_is_rejected(tmp_path):
    with pytest.raises(FinanceError, match="source_window_incomplete"):
        list_payments(
            _payment(), source_window={**WINDOW, "complete": False},
            accounting_period="2026-08", project_evidence=JOIN,
            claims_path=tmp_path / "claims.jsonl",
        )


def test_one_provider_transaction_cannot_enter_two_accounting_periods(tmp_path):
    claims = tmp_path / "claims.jsonl"
    first = list_payments(
        _payment(), source_window=WINDOW, accounting_period="2026-08",
        project_evidence=JOIN, claims_path=claims,
    )
    replay = list_payments(
        _payment(), source_window=WINDOW, accounting_period="2026-08",
        project_evidence=JOIN, claims_path=claims,
    )
    assert replay == first
    assert len(claims.read_text().splitlines()) == 2
    list_payments(
        _payment(), source_window={**WINDOW, "evidence_sha256": "e" * 64},
        accounting_period="2026-08", project_evidence=JOIN, claims_path=claims,
    )
    assert len(claims.read_text().splitlines()) == 2

    september_rows = [
        {**row, "occurred_at": "2026-09-03T05:00:00+00:00"} for row in _payment()
    ]
    with pytest.raises(FinanceError, match="transaction_period_conflict"):
        list_payments(
            september_rows, source_window={**WINDOW, "start": "2026-09-01", "end": "2026-09-30"},
            accounting_period="2026-09", project_evidence=JOIN, claims_path=claims,
        )


def test_payment_and_received_payout_may_cross_accounting_months(tmp_path):
    rows = _payment() + [{
        **_row("payout-1", "payout", 9_000, status="received", related="payment-1"),
        "occurred_at": "2026-09-03T05:00:00+00:00",
    }]
    result = list_payments(
        rows,
        source_window={**WINDOW, "end": "2026-09-30"},
        accounting_period="2026-09", project_evidence=JOIN,
        claims_path=tmp_path / "claims.jsonl",
    )[0]

    assert result["recognized_accounting_period"] == "2026-09"
    assert result["recognized_revenue_usd_minor"] == 9_000
    claims = [json.loads(line) for line in (tmp_path / "claims.jsonl").read_text().splitlines()]
    assert {row["transaction_id"]: row["accounting_period"] for row in claims} == {
        "payment-1": "2026-08", "fee-1": "2026-08", "payout-1": "2026-09",
    }


def test_later_chargeback_is_negative_revenue_in_its_own_month(tmp_path):
    rows = _payment() + [
        _row("payout-1", "payout", 9_000, status="received", related="payment-1"),
        {**_row("chargeback-1", "chargeback", 2_000, status="completed",
                related="payment-1"), "occurred_at": "2026-09-03T05:00:00+00:00"},
    ]
    result = list_payments(
        rows, source_window={**WINDOW, "end": "2026-09-30"},
        accounting_period="2026-09", project_evidence=JOIN,
        claims_path=tmp_path / "claims.jsonl",
    )[0]

    assert result["recognized_accounting_period"] == "2026-09"
    assert result["recognized_revenue_usd_minor"] == -2_000
    assert result["verified_net_usd_minor"] == -2_000
