#!/usr/bin/env python3
"""Authenticated Gmail metadata receiver for immediate Coconala work."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import subprocess
import sys
import threading
from email.utils import parseaddr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


MAX_BODY_BYTES = 262_144
REPLY_SUBJECT_MARKERS = ("メッセージが届いています",)
FULL_PASS_SUBJECT_MARKERS = (
    "トークルームに連絡がありました",
    "提案したサービスが購入されました",
    "【差し戻し】が選択されました",
    "見積り相談",
)


def authorized(header: str, token: str) -> bool:
    if not token:
        return False
    return hmac.compare_digest(str(header or ""), f"Bearer {token}")


def _message_kind(message: Any) -> str | None:
    if not isinstance(message, dict):
        return None
    sender = parseaddr(str(message.get("from") or ""))[1]
    if "@" not in sender or sender.rsplit("@", 1)[-1].lower() != "mail.coconala.com":
        return None
    subject = str(message.get("subject") or "")
    if any(marker in subject for marker in FULL_PASS_SUBJECT_MARKERS):
        return "full_pass"
    if any(marker in subject for marker in REPLY_SUBJECT_MARKERS):
        return "reply"
    return None


def _spawn(command: list[str]) -> None:
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    threading.Thread(target=process.wait, daemon=True).start()


def dispatch_notification(
    payload: Any,
    *,
    detector: Path,
    full_pass_launcher: Path,
    spawn: Callable[[list[str]], None] = _spawn,
) -> str:
    """Route bounded Gmail metadata; never pass external text to a child."""
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
        return "ignored"
    kinds = {_message_kind(message) for message in payload["messages"]}
    if "full_pass" in kinds:
        spawn(["/bin/bash", str(full_pass_launcher)])
        return "full_pass"
    if "reply" in kinds:
        spawn([sys.executable, str(detector), "--trigger", "gmail_push"])
        return "reply"
    return "ignored"


def _env_value(path: Path, key: str) -> str:
    if key in os.environ:
        return os.environ[key]
    if not path.exists():
        return ""
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        if not line.startswith(f"{key}="):
            continue
        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def handler_factory(
    *, token: str, path: str, detector: Path, full_pass_launcher: Path,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != path:
                self.send_error(404)
                return
            if not authorized(self.headers.get("Authorization", ""), token):
                self.send_error(401)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if length <= 0 or length > MAX_BODY_BYTES:
                self.send_error(413 if length > MAX_BODY_BYTES else 400)
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_error(400)
                return
            result = dispatch_notification(
                payload,
                detector=detector,
                full_pass_launcher=full_pass_launcher,
            )
            body = json.dumps({"status": result}, separators=(",", ":")).encode()
            self.send_response(202 if result != "ignored" else 204)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body and result != "ignored":
                self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def main() -> int:
    gig_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--path", default="/coconala-gmail")
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".openclaw/.env")
    parser.add_argument("--token-env", default="GIG_REPLY_HOOK_TOKEN")
    parser.add_argument("--detector", type=Path, default=gig_root / "scripts/reply_detector.py")
    parser.add_argument(
        "--full-pass-launcher", type=Path,
        default=gig_root / "scripts/launch_gig_worker.sh",
    )
    args = parser.parse_args()
    token = _env_value(args.env_file, args.token_env)
    if not token:
        print(f"missing {args.token_env}", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer(
        (args.bind, args.port),
        handler_factory(
            token=token,
            path=args.path,
            detector=args.detector,
            full_pass_launcher=args.full_pass_launcher,
        ),
    )
    server.serve_forever(poll_interval=0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
