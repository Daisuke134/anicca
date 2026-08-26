from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from .mercor_reporting import delivery_state, send_once
from .mercor_work_store import WorkStateStore, WorkStoreError


def sync_result(
    *,
    result_path: Path,
    store_path: Path,
    outbox_path: Path,
    sender: Callable[..., dict[str, Any]] = send_once,
) -> dict[str, Any]:
    value = json.loads(Path(result_path).read_text(encoding="utf-8"))
    events = value.get("mercor_work_events", []) if isinstance(value, dict) else []
    if events is None:
        events = []
    if not isinstance(events, list):
        raise WorkStoreError("mercor_work_events must be an array")
    if not events:
        return {"synced_count": 0, "events": []}
    store = WorkStateStore(store_path)
    receipts: list[dict[str, Any]] = []
    for raw in events:
        if not isinstance(raw, Mapping):
            raise WorkStoreError("mercor work event must be an object")
        required = ("work_id", "event_id", "next_state", "evidence_ref")
        if any(not isinstance(raw.get(field), str) or not raw[field].strip() for field in required):
            raise WorkStoreError("mercor work event has missing identity/evidence fields")
        payment = {
            field: raw[field]
            for field in ("payment_id", "settlement_status", "amount_usd", "reason", "authorization_policy", "acceptance_status")
            if field in raw
        }
        event = store.transition(
            work_id=raw["work_id"].strip(),
            event_id=raw["event_id"].strip(),
            next_state=raw["next_state"].strip(),
            evidence_ref=raw["evidence_ref"].strip(),
            **payment,
        )
        message = (
            "Codex::: Mercor work transition "
            f"work_id={event['work_id']} state={event['state']}"
        )
        try:
            delivery = sender(
                database=outbox_path,
                event_key=f"mercor-work:{event['event_id']}",
                message=message,
            )
            receipt = {**delivery, "delivery": delivery_state(delivery)}
        except Exception as error:  # transition remains durable if reporting fails
            receipt = {"delivery": "delivery_unknown", "reason": type(error).__name__}
        receipts.append({"event_id": event["event_id"], "state": event["state"], **receipt})
    return {"synced_count": len(receipts), "events": receipts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--outbox", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    value = sync_result(result_path=args.result, store_path=args.store, outbox_path=args.outbox)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
