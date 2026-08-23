import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import application_parent  # noqa: E402
import apply_telegram_report  # noqa: E402
import report_envelope  # noqa: E402
from telegram_outbox import TelegramOutbox  # noqa: E402


def test_parent_outlives_the_telegram_transport(tmp_path, monkeypatch):
    calls = []

    class Completed:
        returncode = 0

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(application_parent.subprocess, "run", run)

    application_parent._publish_instant_work_events(
        tmp_path / "applied.jsonl", "pass-1",
    )

    reporter = next(call for call in calls if "apply_telegram_report.py" in str(call[0]))
    assert reporter[1]["timeout"] > 180


def _application_event(event_key: str, occurred_at: int) -> dict:
    return {
        "kind": "application", "event_key": event_key, "entity_id": event_key,
        "occurred_at": datetime.fromtimestamp(occurred_at, timezone.utc).isoformat(),
        "state": "applied", "attributes": {"title": "仕事", "bucket": "one-off"},
        "evidence": [], "next_action": "返信を確認する",
    }


def _delivery_unknown(
    outbox: TelegramOutbox, *, event_key: str, kind: str, message: str, created_at: int,
) -> int:
    row = outbox.enqueue(event_key=event_key, kind=kind, message=message,
                         created_at=created_at, suppress_identical_body=False)
    report_id = int(row["report_id"])
    claimed = outbox.claim(owner="seed", now=created_at, lease_seconds=60, report_id=report_id)
    started = outbox.mark_send_started(report_id, owner="seed", fencing_token=int(claimed["fencing_token"]), now=created_at)
    outbox.mark_delivery_unknown(report_id, owner="seed", fencing_token=int(started["fencing_token"]), error_class="RuntimeError", now=created_at)
    return report_id


def _write_receipt(path: Path, event_key: str, message: str, target: str, ack_at: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(event_key.encode()).hexdigest()
    path = path / f"{name}.json"
    path.write_text(json.dumps({"version": 1, "event_key": event_key, "target": target,
                                "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
                                "message_id": "provider-ack", "provider_acked_at_epoch_ms": ack_at * 1000}) + "\n", encoding="utf-8")


class _Transport:
    def __init__(self, target: str, receipt_dir: Path):
        self.target, self.receipt_dir, self.calls = target, receipt_dir, []

    def send_report(self, message: str, *, event_key: str) -> str:
        self.calls.append((event_key, message))
        return f"ack-{len(self.calls)}"


def test_publish_redrives_only_unresolved_application_events(tmp_path, monkeypatch):
    monkeypatch.delenv("GIG_NOTIFY_EMAIL", raising=False)
    now = int(time.time())
    old = now - 1200
    target = "apply-test-chat"
    receipt_dir = tmp_path / "telegram-delivery-receipts"
    outbox = TelegramOutbox(tmp_path / "telegram-outbox.sqlite3")

    retry_event = _application_event("retry", old)
    receipt_event = _application_event("receipt", old)
    retry_key = f"gig:telegram:instant-work-event:v1:{retry_event['event_key']}"
    receipt_key = f"gig:telegram:instant-work-event:v1:{receipt_event['event_key']}"
    messages = [report_envelope.render_human_ja(report_envelope.build_work_event_envelope(
        work_event=event, observed_at=datetime.now(timezone.utc)))
        for event in (retry_event, receipt_event)]
    retry_message, receipt_message = messages
    for key, kind, message in (
        (retry_key, "application", retry_message),
        (receipt_key, "application", receipt_message),
        ("gig:telegram:foreign:v1:paid", "paid-direct", "foreign lane"),
    ):
        _delivery_unknown(outbox, event_key=key, kind=kind, message=message, created_at=old)
    pending_key = "gig:telegram:instant-work-event:v1:ancient-pending"
    outbox.enqueue(event_key=pending_key, kind="application", message="old pending",
                   created_at=old, suppress_identical_body=False)
    _write_receipt(receipt_dir, receipt_key, receipt_message, target, old)
    _write_receipt(receipt_dir, "gig:telegram:foreign:v1:paid", "foreign lane", target, old)
    (tmp_path / "work-events.jsonl").write_text(json.dumps(receipt_event) + "\n", encoding="utf-8")

    transport = _Transport(target, receipt_dir)
    result = apply_telegram_report.publish(tmp_path, outbox, transport)

    assert result == {"enqueued": 1, "sent": 1, "delivery_unknown": 0}
    assert transport.calls == [(retry_key, retry_message)]
    with outbox._connect() as connection:
        rows = {row["event_key"]: row for row in connection.execute(
            "SELECT * FROM telegram_reports ORDER BY report_id").fetchall()}
    assert (rows[retry_key]["state"], rows[retry_key]["message_id"]) == ("sent", "ack-1")
    assert (rows[receipt_key]["state"], rows[receipt_key]["message_id"]) == ("sent", "provider-ack")
    assert rows["gig:telegram:foreign:v1:paid"]["state"] == "delivery_unknown"
    assert rows[pending_key]["state"] == "pending"


def test_apply_transport_timeout_with_provider_ack_persists_receipt(tmp_path):
    event_key = "gig:telegram:instant-work-event:v1:timeout-ack"

    def timed_out(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 180, output=b'{"messageId":"29117"}\n')

    transport = apply_telegram_report.OpenClawTelegramTransport(target="apply-test-chat", run=timed_out, receipt_dir=tmp_path, now_ms=lambda: 123456)
    assert transport.send_report("verified application", event_key=event_key) == "29117"
    receipt = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert (receipt["message_id"], receipt["event_key"]) == ("29117", event_key)


def test_apply_redrive_reopens_one_row_per_wake(tmp_path):
    old = int(time.time()) - 1200
    outbox = TelegramOutbox(tmp_path / "telegram-outbox.sqlite3")
    for index in range(4):
        _delivery_unknown(outbox, event_key=f"application-{index}", kind="application",
                          message=f"application {index}", created_at=old)

    transport = _Transport("apply-test-chat", tmp_path / "receipts")
    result = apply_telegram_report.publish(tmp_path, outbox, transport)

    assert result["sent"] == 1
    assert len(transport.calls) == 1
    assert outbox.counts().get("delivery_unknown") == 3

    class FailingTransport(_Transport):
        def send_report(self, message: str, *, event_key: str) -> str:
            raise RuntimeError("transport down")

    failed = apply_telegram_report.publish(
        tmp_path, outbox, FailingTransport("apply-test-chat", tmp_path / "receipts")
    )
    assert failed["delivery_unknown"] == 1
    assert outbox.counts().get("pending", 0) == 0
