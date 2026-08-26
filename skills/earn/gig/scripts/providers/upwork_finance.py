#!/usr/bin/env python3
"""Normalize complete Upwork transaction windows without inventing received revenue."""

from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


DIGEST = re.compile(r"[0-9a-f]{64}")
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,127}")
KINDS = {"payment", "fee", "refund", "chargeback", "payout"}
PAYMENT_STATES = {"in_review", "pending", "available", "withdrawn", "reversed"}
AUX_STATES = {"in_review", "pending", "available", "completed", "received", "returned", "reversed"}


class FinanceError(ValueError):
    pass


def _read_window(source_window: Any, accounting_period: str) -> tuple[date, date, str]:
    if (
        not isinstance(source_window, dict)
        or set(source_window) != {"start", "end", "complete", "evidence_sha256"}
        or source_window.get("complete") is not True
        or not DIGEST.fullmatch(str(source_window.get("evidence_sha256") or ""))
        or not re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", accounting_period)
    ):
        raise FinanceError("source_window_incomplete")
    try:
        start, end = date.fromisoformat(source_window["start"]), date.fromisoformat(source_window["end"])
    except (TypeError, ValueError) as exc:
        raise FinanceError("source_window_incomplete") from exc
    period_start = date.fromisoformat(f"{accounting_period}-01")
    if start > end or not start <= period_start <= end:
        raise FinanceError("source_window_incomplete")
    return start, end, source_window["evidence_sha256"]


def _validate_rows(rows: Any, start: date, end: date) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise FinanceError("transactions_invalid")
    required = {
        "transaction_id", "related_payment_id", "contract_id", "milestone_id", "kind",
        "status", "currency", "amount_minor", "occurred_at", "evidence_sha256",
    }
    clean, identities = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise FinanceError("transaction_invalid")
        try:
            occurred = datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise FinanceError("transaction_invalid") from exc
        transaction_id = row["transaction_id"]
        if (
            not KEY.fullmatch(str(transaction_id)) or transaction_id in identities
            or not KEY.fullmatch(str(row["contract_id"])) or not KEY.fullmatch(str(row["milestone_id"]))
            or row["kind"] not in KINDS
            or row["status"] not in (PAYMENT_STATES if row["kind"] == "payment" else AUX_STATES)
            or row["currency"] != "USD" or type(row["amount_minor"]) is not int or row["amount_minor"] < 0
            or occurred.tzinfo is None or occurred.utcoffset() is None
            or not DIGEST.fullmatch(str(row["evidence_sha256"] or ""))
            or not start <= occurred.date() <= end
            or (row["kind"] == "payment" and row["related_payment_id"] is not None)
            or (row["kind"] != "payment" and not KEY.fullmatch(str(row["related_payment_id"] or "")))
        ):
            raise FinanceError("transaction_invalid")
        identities.add(transaction_id); clean.append(dict(row))
    return clean


def _join(project_evidence: Any, contract_id: str) -> dict[str, Any] | None:
    if not isinstance(project_evidence, dict):
        raise FinanceError("project_evidence_invalid")
    value = project_evidence.get(contract_id)
    if value is None:
        return None
    required = {
        "contract_sha256", "submission_id", "delivery_evidence_sha256",
        "execution_id", "execution_cost_usd_minor",
    }
    if (
        not isinstance(value, dict) or set(value) != required
        or not DIGEST.fullmatch(str(value.get("contract_sha256") or ""))
        or not KEY.fullmatch(str(value.get("submission_id") or ""))
        or not DIGEST.fullmatch(str(value.get("delivery_evidence_sha256") or ""))
        or not DIGEST.fullmatch(str(value.get("execution_id") or ""))
        or type(value.get("execution_cost_usd_minor")) is not int
        or value["execution_cost_usd_minor"] < 0
    ):
        raise FinanceError("project_evidence_invalid")
    return value


def _normalize(
    rows: list[dict[str, Any]], project_evidence: dict[str, Any], window_sha: str,
    accounting_period: str,
) -> list[dict[str, Any]]:
    payments = {row["transaction_id"]: row for row in rows if row["kind"] == "payment"}
    related: dict[str, list[dict[str, Any]]] = {identity: [] for identity in payments}
    for row in rows:
        if row["kind"] == "payment":
            continue
        payment_id = row["related_payment_id"]
        if payment_id not in payments:
            raise FinanceError("related_payment_missing")
        related[payment_id].append(row)
    output = []
    for payment_id, payment in sorted(payments.items()):
        children = related[payment_id]
        for child in children:
            if (
                child["contract_id"] != payment["contract_id"]
                or child["milestone_id"] != payment["milestone_id"]
                or child["currency"] != payment["currency"]
            ):
                raise FinanceError("transaction_join_mismatch")
        fees = [row for row in children if row["kind"] == "fee"]
        refunds = [row for row in children if row["kind"] == "refund" and row["status"] == "completed"]
        chargebacks = [row for row in children if row["kind"] == "chargeback" and row["status"] == "completed"]
        payouts = [row for row in children if row["kind"] == "payout" and row["status"] == "received"]
        fee = sum(row["amount_minor"] for row in fees) if fees else None
        refund = sum(row["amount_minor"] for row in refunds)
        chargeback = sum(row["amount_minor"] for row in chargebacks)
        payout_received = sum(row["amount_minor"] for row in payouts) if payouts else None
        payment_period = payment["occurred_at"][:7]
        payout_period = max((row["occurred_at"][:7] for row in payouts), default=None)
        payout_cutoff = max((datetime.fromisoformat(row["occurred_at"]) for row in payouts), default=None)
        adjustments = [*refunds, *chargebacks]
        adjustment_periods = {row["occurred_at"][:7] for row in adjustments}
        before_payout = sum(
            row["amount_minor"] for row in adjustments
            if payout_cutoff is not None and datetime.fromisoformat(row["occurred_at"]) <= payout_cutoff
        )
        later_current = sum(
            row["amount_minor"] for row in adjustments
            if payout_cutoff is not None and datetime.fromisoformat(row["occurred_at"]) > payout_cutoff
            and row["occurred_at"][:7] == accounting_period
        )
        expected_at_payout = (
            payment["amount_minor"] - fee - before_payout if fee is not None else None
        )
        if accounting_period not in {payment_period, payout_period, *adjustment_periods}:
            continue
        evidence = _join(project_evidence, payment["contract_id"])
        payout_complete = (
            payment["status"] in {"available", "withdrawn"}
            and expected_at_payout is not None and expected_at_payout >= 0
            and payout_received == expected_at_payout and evidence is not None
        )
        recognized = verified_net = None
        if payout_complete and payout_period == accounting_period:
            recognized = expected_at_payout - later_current
            verified_net = recognized - evidence["execution_cost_usd_minor"]
        elif payout_complete and later_current:
            recognized = verified_net = -later_current
        output.append({
            "provider": "upwork", "payment_id": payment_id,
            "provider_transaction_ids": sorted(row["transaction_id"] for row in [payment, *children]),
            "contract_id": payment["contract_id"], "milestone_id": payment["milestone_id"],
            "currency": "USD", "state": payment["status"],
            "gross_usd_minor": payment["amount_minor"], "fee_usd_minor": fee,
            "refund_usd_minor": refund, "chargeback_usd_minor": chargeback,
            "payout_available": bool(payment["status"] == "available" and not payouts),
            "payout_transaction_ids": sorted(row["transaction_id"] for row in payouts),
            "recognized_accounting_period": accounting_period if recognized is not None else None,
            "recognized_revenue_usd_minor": recognized,
            "contract_sha256": evidence["contract_sha256"] if evidence else None,
            "submission_id": evidence["submission_id"] if evidence else None,
            "delivery_evidence_sha256": evidence["delivery_evidence_sha256"] if evidence else None,
            "execution_id": evidence["execution_id"] if evidence else None,
            "execution_cost_usd_minor": evidence["execution_cost_usd_minor"] if evidence else None,
            "verified_net_usd_minor": verified_net,
            "source_window_sha256": window_sha,
        })
    return output


def _claim(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path = path.expanduser(); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    with path.open("a+", encoding="utf-8") as handle:
        os.chmod(path, 0o600); fcntl.flock(handle.fileno(), fcntl.LOCK_EX); handle.seek(0)
        existing = {}
        for line in handle:
            try:
                claim = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FinanceError("transaction_claims_invalid") from exc
            if not isinstance(claim, dict) or set(claim) != {"transaction_id", "accounting_period", "transaction_evidence_sha256"}:
                raise FinanceError("transaction_claims_invalid")
            prior = existing.setdefault(claim["transaction_id"], claim)
            if prior != claim:
                raise FinanceError("transaction_claims_invalid")
        pending = []
        for row in rows:
            period = row["occurred_at"][:7]
            claim = {"transaction_id": row["transaction_id"], "accounting_period": period,
                     "transaction_evidence_sha256": row["evidence_sha256"]}
            prior = existing.get(row["transaction_id"])
            if prior is not None and prior["accounting_period"] != period:
                raise FinanceError("transaction_period_conflict")
            if prior is not None and prior != claim:
                raise FinanceError("transaction_claim_changed")
            if prior is None:
                pending.append(claim); existing[row["transaction_id"]] = claim
        for claim in pending:
            handle.write(json.dumps(claim, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def list_payments(
    rows: list[dict[str, Any]], *, source_window: dict[str, Any], accounting_period: str,
    project_evidence: dict[str, Any], claims_path: str | Path,
) -> list[dict[str, Any]]:
    """Return payment truth; only a matching received payout becomes recognized revenue."""
    start, end, window_sha = _read_window(source_window, accounting_period)
    clean = _validate_rows(rows, start, end)
    result = _normalize(clean, project_evidence, window_sha, accounting_period)
    _claim(Path(claims_path), clean)
    return result
