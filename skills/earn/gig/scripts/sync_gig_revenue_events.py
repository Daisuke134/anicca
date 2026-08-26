#!/usr/bin/env python3
"""Project evidence-backed Coconala settlements into the shared economics ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))

try:  # The shared event helper is optional in a source-only checkout; candidate projection stays usable.
    from unit_economics_events import append_event, make_event  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - exercised only by incomplete source installs
    append_event = make_event = None  # type: ignore[assignment]


SETTLED = {"SETTLED", "settled", "検収", "検収完了", "支払", "支払完了"}


def build_revenue_candidate(row: dict[str, Any], *, recipient: str | None = None) -> dict[str, Any]:
    """Return a proof-bound Coconala candidate without treating net-only UI as revenue.

    ``earnings.jsonl`` historically stores the post-fee ``jpy`` amount and an evidence URL.  That
    is useful for the gig funnel but is not a provider payout receipt.  The shared v2 adapter only
    consumes this projection when gross, fee, payer, recipient, and a verified payout receipt are
    all present.  Otherwise this function returns a durable, secret-free rejection projection.
    """
    if not isinstance(row, dict):
        return {"kind": "revenue_rejection", "provider": "coconala", "reason": "source_row_invalid"}
    source_id = str(row.get("requestId") or row.get("request_id") or "").strip()
    proof = row.get("proof") if isinstance(row.get("proof"), dict) else None
    payout_id = (proof or {}).get("provider_receipt_id") or row.get("payout_receipt_id") or row.get("payoutReceiptId")
    verified = (proof or {}).get("verified") is True or row.get("payout_proof_verified") is True
    payout_status = str(row.get("payout_status") or row.get("payoutState") or "").strip().lower()
    gross = row.get("gross_jpy", row.get("gross_amount_jpy", row.get("gross_amount")))
    fee = row.get("fee_jpy", row.get("fee_amount_jpy", row.get("fee_amount")))
    payer = row.get("payer") or row.get("buyer_id") or row.get("buyerId") or row.get("buyer")
    destination = row.get("recipient") or row.get("recipient_id") or recipient
    missing = []
    if row.get("status") not in SETTLED: missing.append("terminal_state")
    if row.get("net_of_fee") is True and gross is None: missing.append("gross")
    if gross is None: missing.append("gross")
    if fee is None: missing.append("fee")
    if not isinstance(payer, str) or not payer.strip(): missing.append("payer")
    if not isinstance(destination, str) or not destination.strip(): missing.append("recipient")
    if not payout_id or not verified: missing.append("verified_payout_proof")
    if payout_status in {"pending", "requested", "申請済み", "in_transit"}: missing.append("terminal_payout")
    if missing:
        return {
            "kind": "revenue_rejection", "provider": "coconala", "source_record_id": source_id,
            "reason": "missing_or_unverified_settlement:" + ",".join(dict.fromkeys(missing)),
        }
    return {
        "provider": "coconala", "requestId": source_id, "payer": str(payer).strip(),
        "recipient": str(destination).strip(), "gross_jpy": gross, "fee_jpy": fee,
        "refund_jpy": row.get("refund_jpy", 0), "payout_jpy": row.get("payout_jpy"),
        "asset": "JPY", "status": row["status"], "occurred_at": row.get("occurred_at", row.get("ts")),
        "proof": {"provider_receipt_id": str(payout_id).strip(), "verified": True},
    }


def revenue_candidates(rows: list[dict[str, Any]], *, recipient: str | None = None) -> list[dict[str, Any]]:
    """Project a Coconala source snapshot to accepted/rejected provider-proof candidates."""
    return [build_revenue_candidate(row, recipient=recipient) for row in (rows if isinstance(rows, list) else [])]


revenue_candidate = build_revenue_candidate


def _source_record_id(row: dict[str, Any]) -> str:
    bounded = {
        "request_id": row.get("requestId") or row.get("request_id"),
        "status": row.get("status"),
        "evidence": row.get("evidence") or row.get("proof"),
    }
    return hashlib.sha256(
        json.dumps(bounded, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sync_gig_revenue(earnings_path: str | Path, ledger_path: str | Path) -> dict[str, int]:
    result = {"scanned": 0, "eligible": 0, "appended": 0, "duplicates": 0, "rejected": 0}
    source = Path(earnings_path).expanduser().resolve()
    if not source.exists():
        return result
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            result["scanned"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                result["rejected"] += 1
                continue
            if not isinstance(row, dict):
                result["rejected"] += 1
                continue
            candidate = build_revenue_candidate(row)
            if candidate.get("kind") == "revenue_rejection":
                result["rejected"] += 1
                continue
            result["eligible"] += 1
            try:
                if append_event is None or make_event is None:
                    raise ValueError("unit economics event helper is unavailable")
                amount = candidate.get("payout_jpy")
                if amount is None:
                    amount = int(candidate["gross_jpy"]) - int(candidate["fee_jpy"])
                if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                    raise ValueError("signed net is not a positive JPY integer")
                event = make_event(
                    kind="revenue",
                    loop="gig",
                    source="anicca://gig/coconala",
                    source_record_id=_source_record_id(candidate),
                    occurred_at=candidate["occurred_at"],
                    amount_minor=amount,
                    currency="JPY",
                    evidence=row.get("evidence") or json.dumps(candidate["proof"], sort_keys=True),
                )
                if append_event(ledger_path, event):
                    result["appended"] += 1
                else:
                    result["duplicates"] += 1
            except (OSError, ValueError):
                result["rejected"] += 1
    return result


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--earnings", type=Path, default=Path("~/gig/earnings.jsonl").expanduser())
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("~/.local/state/anicca/telemetry/unit-economics-events.jsonl").expanduser(),
    )
    args = parser.parse_args()
    result = sync_gig_revenue(args.earnings, args.ledger)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
