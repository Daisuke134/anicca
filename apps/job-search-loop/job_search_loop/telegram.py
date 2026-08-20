from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from .outbox import Outbox


TelegramRequester = Callable[..., dict[str, Any]]


class TelegramRejected(RuntimeError):
    """The Telegram API returned an explicit non-delivery response."""


def _telegram_config_value(config_name: str, supplied: str | None) -> str:
    """Read private Telegram configuration without putting it in a release."""
    if supplied:
        return supplied
    value = os.environ.get(config_name)
    if value:
        return value
    env_file = Path(
        os.environ.get(
            "JOB_SEARCH_TELEGRAM_ENV",
            str(Path.home() / ".config" / "anicca" / "job-search" / "telegram.env"),
        )
    ).expanduser()
    if not env_file.is_file():
        raise RuntimeError(f"{config_name} is unavailable")
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed_name, separator, encoded = line.removeprefix("export ").partition("=")
        if separator and parsed_name.strip() == config_name:
            values = shlex.split(encoded, comments=True, posix=True)
            if len(values) == 1 and values[0]:
                return values[0]
    raise RuntimeError(f"{config_name} is unavailable")


def _telegram_token(token: str | None) -> str:
    return _telegram_config_value("TELEGRAM_BOT_TOKEN", token)


def _telegram_target(target: str | None) -> str:
    return _telegram_config_value("JOB_SEARCH_TELEGRAM_CHAT_ID", target)


def _telegram_request(
    *,
    method: str,
    token: str,
    fields: dict[str, str],
    document: Path | None = None,
) -> dict[str, Any]:
    """Call Telegram, retrying once with a DNS answer when system DNS is empty."""
    base_url = os.environ.get(
        "TELEGRAM_BOT_API_BASE_URL", "https://api.telegram.org/bot"
    ).rstrip("/")
    url = f"{base_url}{token}/{method}"
    host = "api.telegram.org"
    curl = shutil.which("curl") or "/usr/bin/curl"

    def command(resolve: str | None = None) -> list[str]:
        args = [curl, "-sS", "--max-time", "60"]
        if resolve:
            args.extend(["--resolve", f"{host}:443:{resolve}"])
        if document is None:
            args.extend(
                [
                    "-H",
                    "Content-Type: application/json",
                    "--data-binary",
                    json.dumps(fields, ensure_ascii=False),
                ]
            )
        else:
            args.extend(
                [
                    "--form",
                    f"chat_id={fields['chat_id']}",
                    "--form",
                    f"caption={fields['caption']}",
                    "--form",
                    f"document=@{document};type=application/octet-stream",
                ]
            )
        args.append(url)
        return args

    completed = subprocess.run(
        command(), check=False, capture_output=True, text=True, timeout=70
    )
    if completed.returncode != 0 and base_url.startswith("https://api.telegram.org"):
        resolved = subprocess.run(
            [
                "dig",
                "+short",
                "+time=2",
                "+tries=1",
                "@1.1.1.1",
                host,
                "A",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        address = next(
            (
                line.strip()
                for line in resolved.stdout.splitlines()
                if line.strip().count(".") == 3
            ),
            None,
        )
        if address:
            completed = subprocess.run(
                command(address),
                check=False,
                capture_output=True,
                text=True,
                timeout=70,
            )
    if completed.returncode != 0:
        raise RuntimeError(f"Telegram transport failed rc={completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Telegram transport returned invalid JSON") from exc
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise TelegramRejected("Telegram Bot API rejected the request")
    return result


def _message_id(result: dict[str, Any]) -> str:
    payload = result.get("result")
    message_id = payload.get("message_id") if isinstance(payload, dict) else None
    if message_id is None:
        raise RuntimeError("Telegram ACK has no message ID")
    return str(message_id)


def send_daily_report(
    *,
    database: Path,
    japan_day: str,
    message: str,
    target: str | None = None,
    token: str | None = None,
    requester: TelegramRequester = _telegram_request,
    executable: str | None = None,
    material_digest: str | None = None,
) -> dict[str, str | None]:
    base_key = f"job-search-daily:{japan_day}"
    if material_digest is not None:
        if len(material_digest) != 64 or any(
            character not in "0123456789abcdef" for character in material_digest
        ):
            raise ValueError("daily material digest is invalid")
        base_key = f"{base_key}:state:{material_digest[:16]}"
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
        token=token,
        requester=requester,
        executable=executable,
    )
    return {**result, "event_key": event_key}


def send_once(
    *,
    database: Path,
    event_key: str,
    message: str,
    target: str | None = None,
    token: str | None = None,
    requester: TelegramRequester = _telegram_request,
    executable: str | None = None,
) -> dict[str, str | None]:
    outbox = Outbox(database)
    try:
        outbox.enqueue(event_key, message)
        existing = outbox.status(event_key)
        if existing["status"] == "sent":
            return existing
        fence = outbox.claim(event_key)
        outbox.mark_send_started(event_key, fence)
        if executable is not None:
            completed = subprocess.run(
                [
                    executable,
                    "message",
                    "send",
                    "--channel",
                    "telegram",
                    "--target",
                    target or "0000000000",
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
        else:
            try:
                result = requester(
                    method="sendMessage",
                    token=_telegram_token(token),
                    fields={"chat_id": _telegram_target(target), "text": outbox.payload(event_key)},
                )
            except TelegramRejected:
                outbox.mark_failed(event_key, fence)
                raise
            outbox.mark_sent(event_key, fence, _message_id(result))
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
    target: str | None = None,
    token: str | None = None,
    requester: TelegramRequester = _telegram_request,
    executable: str | None = None,
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

        fence = outbox.claim(event_key)
        outbox.mark_send_started(event_key, fence)
        if executable is not None:
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
            completed = subprocess.run(
                [
                    executable,
                    "message",
                    "send",
                    "--channel",
                    "telegram",
                    "--target",
                    target or "0000000000",
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
                raise RuntimeError("Telegram ACK has no message ID")
            outbox.mark_sent(event_key, fence, str(message_id))
        else:
            try:
                result = requester(
                    method="sendDocument",
                    token=_telegram_token(token),
                    fields={
                        "chat_id": _telegram_target(target),
                        "caption": outbox.payload(event_key),
                    },
                    document=source,
                )
            except TelegramRejected:
                outbox.mark_failed(event_key, fence)
                raise
            outbox.mark_sent(event_key, fence, _message_id(result))
        return outbox.status(event_key)
    finally:
        outbox.close()
