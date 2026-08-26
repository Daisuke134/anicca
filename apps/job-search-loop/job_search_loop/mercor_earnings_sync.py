from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

from .mercor_earnings import build_earnings_result
from .mercor_reporting import delivery_state
from .mercor_work_store import WorkStateStore, WorkStoreError
from .telegram import send_once


def sync_earnings_snapshot(
    *,
    snapshot_path: Path,
    store_path: Path,
    outbox_path: Path,
    sender: Callable[..., dict[str, Any]] = send_once,
) -> dict[str, Any]:
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    result = build_earnings_result(snapshot)
    if not result["settled_rows"]:
        return {"status": result["status"], "synced_count": 0, "events": []}
    store = WorkStateStore(store_path)
    receipts: list[dict[str, Any]] = []
    for row in result["settled_rows"]:
        work_id = row.get("work_id")
        if not isinstance(work_id, str) or not work_id.strip():
            raise WorkStoreError("settled payout must map to a work_id")
        payment_id = row["payment_id"]
        evidence_ref = f"{result['page_url']}#{payment_id}"
        paid = store.transition(
            work_id=work_id,
            event_id=f"payout:{payment_id}",
            next_state="paid_settled",
            evidence_ref=evidence_ref,
            payment_id=payment_id,
            settlement_status=row["status"],
            amount_usd=str(row["earned_usd"]),
        )
        revenue = store.transition(
            work_id=work_id,
            event_id=f"revenue:{payment_id}",
            next_state="revenue_recorded",
            evidence_ref=evidence_ref,
        )
        message = f"Codex::: Mercor settled payout work_id={work_id} payment_id={payment_id} amount_usd={row['earned_usd']}"
        try:
            delivery = sender(
                database=outbox_path,
                event_key=f"mercor-payout:{payment_id}",
                message=message,
            )
            receipt = {**delivery, "delivery": delivery_state(delivery)}
        except Exception as error:
            receipt = {"delivery": "delivery_unknown", "reason": type(error).__name__}
        receipts.append({"payment_id": payment_id, "state": revenue["state"], **receipt})
    return {"status": "settled", "synced_count": len(receipts), "events": receipts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--outbox", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    value = sync_earnings_snapshot(
        snapshot_path=args.snapshot,
        store_path=args.store,
        outbox_path=args.outbox,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
