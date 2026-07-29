from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from .outbox import Outbox


def send_daily_report(
    *,
    database: Path,
    japan_day: str,
    message: str,
    target: str = "0000000000",
    executable: str = "/opt/homebrew/bin/openclaw",
) -> dict[str, str | None]:
    base_key = f"job-search-daily:{japan_day}"
    outbox = Outbox(database)
    try:
        existing = outbox.connection.execute(
            "SELECT payload FROM outbox WHERE event_key=?",
            (base_key,),
        ).fetchone()
    finally:
        outbox.close()

    if existing is None or str(existing[0]) == message:
        event_key = base_key
    else:
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
        event_key = f"{base_key}:correction:{digest}"

    result = send_once(
        database=database,
        event_key=event_key,
        message=message,
        target=target,
        executable=executable,
    )
    return {**result, "event_key": event_key}


def send_once(
    *,
    database: Path,
    event_key: str,
    message: str,
    target: str = "0000000000",
    executable: str = "/opt/homebrew/bin/openclaw",
) -> dict[str, str | None]:
    outbox = Outbox(database)
    try:
        outbox.enqueue(event_key, message)
        existing = outbox.status(event_key)
        if existing["status"] == "sent":
            return existing
        fence = outbox.claim(event_key)
        outbox.mark_send_started(event_key, fence)
        completed = subprocess.run(
            [
                executable,
                "message",
                "send",
                "--channel",
                "telegram",
                "--target",
                target,
                "--message",
                outbox.payload(event_key),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Telegram transport failed rc={completed.returncode}")
        result = json.loads(completed.stdout)
        payload = result.get("payload", {}) if isinstance(result, dict) else {}
        message_id = result.get("messageId") or payload.get("messageId")
        if not message_id:
            raise RuntimeError("Telegram ACK has no message ID")
        outbox.mark_sent(event_key, fence, str(message_id))
        return outbox.status(event_key)
    finally:
        outbox.close()


def send_document_once(
    *,
    database: Path,
    event_key: str,
    message: str,
    document: Path,
    media_root: Path,
    target: str = "0000000000",
    executable: str = "/opt/homebrew/bin/openclaw",
) -> dict[str, str | None]:
    outbox = Outbox(database)
    try:
        outbox.enqueue(event_key, message)
        existing = outbox.status(event_key)
        if existing["status"] == "sent":
            return existing

        source = Path(document).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"Telegram document is not a file: {source}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        safe_name = "".join(
            character
            for character in source.name
            if character.isalnum() or character in "._-"
        ) or "resume.pdf"
        staging_root = Path(media_root).expanduser().resolve()
        staging_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(staging_root, 0o700)
        staged = staging_root / f"{digest[:16]}-{safe_name}"
        shutil.copyfile(source, staged)
        os.chmod(staged, 0o600)

        fence = outbox.claim(event_key)
        outbox.mark_send_started(event_key, fence)
        completed = subprocess.run(
            [
                executable,
                "message",
                "send",
                "--channel",
                "telegram",
                "--target",
                target,
                "--message",
                outbox.payload(event_key),
                "--media",
                str(staged),
                "--force-document",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Telegram document transport failed rc={completed.returncode}"
            )
        result = json.loads(completed.stdout)
        payload = result.get("payload", {}) if isinstance(result, dict) else {}
        message_id = result.get("messageId") or payload.get("messageId")
        if not message_id:
            raise RuntimeError("Telegram document ACK has no message ID")
        outbox.mark_sent(event_key, fence, str(message_id))
        return outbox.status(event_key)
    finally:
        outbox.close()
