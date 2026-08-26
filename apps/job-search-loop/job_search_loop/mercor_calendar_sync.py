from __future__ import annotations

from typing import Any, Callable, Mapping

from .mercor_work_store import WorkStateStore
from .mercor_reporting import delivery_state
from .telegram import send_once


def sync_calendar_events(
    *,
    payload: Mapping[str, Any],
    store_path,
    outbox_path,
    sender: Callable[..., dict[str, Any]] = send_once,
) -> dict[str, Any]:
    events = payload.get("mercor_calendar_events", [])
    if events is None:
        events = []
    if not isinstance(events, list):
        raise ValueError("mercor_calendar_events must be an array")
    store = WorkStateStore(store_path)
    receipts: list[dict[str, Any]] = []
    for row in events:
        if not isinstance(row, Mapping):
            raise ValueError("Mercor calendar event must be an object")
        required = ("work_id", "event_id", "calendar_event_key", "evidence_ref")
        if any(not isinstance(row.get(field), str) or not row[field].strip() for field in required):
            raise ValueError("Mercor calendar event has missing fields")
        artifact = store.record_artifact(
            work_id=row["work_id"].strip(),
            event_id=row["event_id"].strip(),
            artifact_type="calendar_scheduled",
            artifact_key=row["calendar_event_key"].strip(),
            evidence_ref=row["evidence_ref"].strip(),
        )
        message = f"Codex::: Mercor calendar work_id={artifact['work_id']} key={artifact['artifact_key']}"
        try:
            delivery = sender(
                database=outbox_path,
                event_key=f"mercor-calendar:{artifact['event_id']}",
                message=message,
            )
            receipt = {**delivery, "delivery": delivery_state(delivery)}
        except Exception as error:
            receipt = {"delivery": "delivery_unknown", "reason": type(error).__name__}
        receipts.append({"event_id": artifact["event_id"], **receipt})
    return {"synced_count": len(receipts), "events": receipts}
