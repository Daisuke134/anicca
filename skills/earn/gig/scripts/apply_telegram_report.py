#!/usr/bin/env python3
"""Publish verified Apply work events without importing another revenue lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import report_envelope
from telegram_outbox import TelegramOutbox, dispatch_one
from owner_notify import send_email_if_configured


def _jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _timestamp(value: Any) -> datetime:
    moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _read_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    value = json.loads(path.read_text(encoding="utf-8"))
    keys = value.get("seen_event_keys") if isinstance(value, dict) else None
    if value.get("version") != 1 or not isinstance(keys, list):
        raise ValueError("apply_report_state_invalid")
    return {str(key) for key in keys if isinstance(key, str) and key}


def _write_seen(path: Path, keys: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "seen_event_keys": sorted(keys)}, handle,
                      ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class OpenClawTelegramTransport:
    def __init__(
        self, *, target: str, executable: Path = Path("/opt/homebrew/bin/openclaw"),
        receipt_dir: Path | None = None, run: Callable[..., Any] = subprocess.run,
        now_ms: Callable[[], int] | None = None,
    ):
        self.target = str(target)
        self.executable = Path(executable)
        self.receipt_dir = Path(receipt_dir or Path.home() / "gig/telegram-delivery-receipts")
        self.run = run
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))

    def send_report(self, message: str, *, event_key: str) -> str:
        message_id = send_email_if_configured(message, event_key=event_key, run=self.run)
        if message_id is None:
            command = [
                str(self.executable), "message", "send", "--channel", "telegram",
                "--target", self.target, "--message", message, "--json",
            ]
            try:
                completed = self.run(
                    command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                    timeout=180, check=False,
                )
                if completed.returncode != 0:
                    raise RuntimeError(f"Telegram transport failed rc={completed.returncode}")
                provider_output = completed.stdout
            except subprocess.TimeoutExpired as error:
                provider_output = error.stdout
                if not provider_output:
                    raise
            if isinstance(provider_output, bytes):
                provider_output = provider_output.decode("utf-8", errors="strict")
            try:
                result = json.loads(provider_output)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError("Telegram transport returned invalid JSON") from error
            payload = result.get("payload") if isinstance(result, dict) else None
            if isinstance(payload, dict) and payload.get("ok") is False:
                raise RuntimeError("Telegram provider rejected message")
            message_id = result.get("messageId") if isinstance(result, dict) else None
            if not message_id and isinstance(payload, dict):
                message_id = payload.get("messageId")
            if not message_id:
                raise RuntimeError("Telegram ACK has no message ID")
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(event_key.encode()).hexdigest()
        receipt = {
            "version": 1, "event_key": event_key,
            "target": os.environ.get("GIG_NOTIFY_EMAIL", "").strip() or self.target,
            "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
            "message_id": str(message_id),
            "provider_acked_at_epoch_ms": int(self.now_ms()),
        }
        fd, temporary = tempfile.mkstemp(prefix=f".{digest}.", dir=self.receipt_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(receipt, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.receipt_dir / f"{digest}.json")
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        return str(message_id)


def publish(gig_dir: Path, outbox: TelegramOutbox, transport: OpenClawTelegramTransport) -> dict:
    now_epoch = int(time.time())
    outbox.reconcile_receipts(
        receipt_dir=transport.receipt_dir,
        target=os.environ.get("GIG_NOTIFY_EMAIL", "").strip() or transport.target,
        now=now_epoch,
        kinds=("application",),
    )
    redrive_report_ids = outbox.redrive_unresolved_report_ids(
        now=now_epoch, kinds=("application",), limit=1,
    )
    seen_path = gig_dir / "instant-work-event-report-state.json"
    seen = _read_seen(seen_path)
    fresh_report_ids: list[int] = []
    existing_pending_ids: list[int] = []
    enqueued = 0
    for event in _jsonl(gig_dir / "work-events.jsonl"):
        if event.get("kind") != "application" or not event.get("event_key"):
            continue
        try:
            occurred = _timestamp(event.get("occurred_at"))
        except (TypeError, ValueError):
            continue
        if occurred.timestamp() < now_epoch - 86400:
            continue
        event_key = str(event["event_key"])
        outbox_key = f"gig:telegram:instant-work-event:v1:{event_key}"
        envelope = report_envelope.build_work_event_envelope(
            work_event=event, observed_at=datetime.now(timezone.utc),
        )
        is_fresh = event_key not in seen
        if is_fresh:
            report_envelope.append_agent_feed(gig_dir / "report-envelopes.jsonl", envelope)
            seen.add(event_key)
            enqueued += 1
        queued = outbox.enqueue(
            event_key=outbox_key, kind="application",
            message=report_envelope.render_human_ja(envelope), created_at=now_epoch,
            suppress_identical_body=False,
        )
        if queued.get("state") == "pending":
            target = fresh_report_ids if is_fresh else existing_pending_ids
            target.append(int(queued["report_id"]))
    _write_seen(seen_path, seen)
    sent = unknown = 0
    dispatch_ids = list(dict.fromkeys([
        *fresh_report_ids, *existing_pending_ids, *redrive_report_ids,
    ]))
    for report_id in dispatch_ids:
        result = dispatch_one(
            outbox, owner=f"gig-apply-telegram:{uuid.uuid4().hex}",
            now=lambda: int(time.time()), transport=transport, report_id=report_id,
        )
        sent += int(result["status"] == "sent")
        unknown += int(result["status"] == "delivery_unknown")
        if unknown:
            break
    return {"enqueued": enqueued, "sent": sent, "delivery_unknown": unknown}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gig-dir", type=Path, default=Path.home() / "gig")
    parser.add_argument("--telegram-database", type=Path,
                        default=Path.home() / "gig/telegram-outbox.sqlite3")
    parser.add_argument("--target", default=os.environ.get("GIG_REPORT_CHAT", ""))
    parser.add_argument("--openclaw", type=Path, default=Path("/opt/homebrew/bin/openclaw"))
    args = parser.parse_args()
    outbox = TelegramOutbox(args.telegram_database)
    outbox.recover_expired(now=int(time.time()))
    transport = OpenClawTelegramTransport(
        target=args.target, executable=args.openclaw,
        receipt_dir=args.gig_dir / "telegram-delivery-receipts",
    )
    print(json.dumps(publish(args.gig_dir, outbox, transport), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
