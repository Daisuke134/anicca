#!/usr/bin/env python3
"""Project evidence-backed Coconala settlements into the shared economics ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))

try:  # The shared event helper is optional in a source-only checkout; candidate projection stays usable.
    from unit_economics_events import append_event, make_event  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - exercised only by incomplete source installs
    def make_event(**kwargs: Any) -> dict[str, Any]:
        """Compatibility implementation for the historical helper missing from this checkout."""
        required = ("kind", "loop", "source", "source_record_id", "occurred_at", "amount_minor", "currency", "evidence")
        if any(key not in kwargs for key in required):
            raise ValueError("unit economics event fields are incomplete")
        if isinstance(kwargs["amount_minor"], bool) or not isinstance(kwargs["amount_minor"], int) or kwargs["amount_minor"] <= 0:
            raise ValueError("amount_minor must be a positive integer")
        return dict(kwargs)

    def append_event(path: str | Path, event: dict[str, Any]) -> bool:
        """Append once by source_record_id, matching the real helper's replay-zero contract."""
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        seen: set[str] = set()
        if target.exists():
            for line in target.read_text(encoding="utf-8").splitlines():
                try:
                    stored = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(stored, dict) and stored.get("source_record_id"):
                    seen.add(str(stored["source_record_id"]))
        if str(event["source_record_id"]) in seen:
            return False
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return True


SETTLED = {"SETTLED", "settled", "検収", "検収完了", "支払", "支払完了"}
REVENUE_PROJECTOR = Path(__file__).resolve().parents[4] / "skills" / "agent-economy" / "lib" / "revenue-adapters.mjs"


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
    if not payout_id: missing.append("payout_proof_id")
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
        # Deliberately unverified: only the JavaScript official-verifier boundary can attest this id.
        "proof": {"provider_receipt_id": str(payout_id).strip()},
    }


def revenue_candidates(rows: list[dict[str, Any]], *, recipient: str | None = None) -> list[dict[str, Any]]:
    """Project a Coconala source snapshot to accepted/rejected provider-proof candidates."""
    return [build_revenue_candidate(row, recipient=recipient) for row in (rows if isinstance(rows, list) else [])]


revenue_candidate = build_revenue_candidate


def invoke_revenue_projector(
    source_path: str | Path, *, provider: str = "coconala", journal_path: str | Path | None = None,
    rejection_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the deterministic shared projector after the durable provider source is read.

    The CLI has no trusted verifier context, so it can persist rejection evidence but cannot turn a
    raw payout id into revenue.  A trusted embedding caller supplies an official verifier directly
    to ``projectRevenueReceipts`` for a future live canary.
    """
    source = Path(source_path).expanduser().resolve()
    journal = Path(journal_path or source.with_name("revenue-receipts.jsonl")).expanduser().resolve()
    rejection = Path(rejection_path or source.with_name("revenue-rejections.jsonl")).expanduser().resolve()
    completed = subprocess.run(
        [os.environ.get("NODE", "node"), str(REVENUE_PROJECTOR), "--provider", provider,
         "--rows", str(source), "--journal", str(journal), "--rejections", str(rejection)],
        text=True, capture_output=True, timeout=30, check=False,
    )
    if completed.returncode != 0:
        return {"ok": False, "error": "revenue_projector_failed"}
    try:
        value = json.loads(completed.stdout)
    except (TypeError, ValueError):
        return {"ok": False, "error": "revenue_projector_invalid_output"}
    return value if isinstance(value, dict) else {"ok": False, "error": "revenue_projector_invalid_output"}


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
            if (
                row.get("status") not in SETTLED
                or not isinstance(row.get("requestId"), str)
                or not row["requestId"].strip()
                or not isinstance(row.get("jpy"), int)
                or isinstance(row.get("jpy"), bool)
                or row["jpy"] <= 0
                or not isinstance(row.get("evidence"), str)
                or not row["evidence"].strip()
                or row.get("ts") is None
            ):
                result["rejected"] += 1
                continue
            result["eligible"] += 1
            try:
                if append_event is None or make_event is None:
                    raise ValueError("unit economics event helper is unavailable")
                event = make_event(
                    kind="revenue",
                    loop="gig",
                    source="anicca://gig/coconala",
                    source_record_id=_source_record_id(row),
                    occurred_at=row["ts"],
                    amount_minor=row["jpy"],
                    currency="JPY",
                    evidence=row["evidence"],
                )
                if append_event(ledger_path, event):
                    result["appended"] += 1
                else:
                    result["duplicates"] += 1
            except (OSError, ValueError):
                result["rejected"] += 1
    # The legacy unit-economics event remains historically unchanged; the shared adapter projection
    # runs separately and fail-closed after the same durable source has been observed.
    try:
        invoke_revenue_projector(
            source,
            provider="coconala",
            journal_path=os.environ.get("REVENUE_RECEIPT_JOURNAL"),
            rejection_path=os.environ.get("REVENUE_RECEIPT_REJECTIONS"),
        )
    except (OSError, subprocess.SubprocessError):
        pass
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
