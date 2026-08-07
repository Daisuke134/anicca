#!/usr/bin/env python3
"""Send a compact Telegram progress brief for recently active Codex sessions."""

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ACTIVE_WINDOW_SECONDS = 20 * 60
STALLED_AFTER_SECONDS = 10 * 60
MAX_SESSIONS = 8


def session_label(path):
    match = re.search(r"-([0-9a-f]{3,})\.jsonl$", path.name)
    return match.group(1)[:8] if match else path.stem[-8:]


def latest_progress_message(path):
    latest = None
    try:
        with path.open(encoding="utf-8") as session_file:
            for line in session_file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = event.get("payload", {})
                if event.get("type") == "event_msg" and payload.get("type") == "agent_message":
                    message = payload.get("message", "").strip()
                    if message:
                        latest = message
    except OSError:
        return None
    return latest


def session_summary(path, now=None, modified_at=None):
    now = time.time() if now is None else now
    modified_at = path.stat().st_mtime if modified_at is None else modified_at
    age = max(0, int(now - modified_at))
    if age >= STALLED_AFTER_SECONDS:
        status = "停滞の可能性"
    else:
        status = "作業中"
    update = latest_progress_message(path) or "最後の進捗メッセージを待機中"
    update = " ".join(update.split())[:240]
    return {"label": session_label(path), "status": status, "update": update, "age": age}


def active_sessions(sessions_root, now=None):
    now = time.time() if now is None else now
    paths = sorted(sessions_root.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        session_summary(path, now=now)
        for path in paths[:MAX_SESSIONS]
        if now - path.stat().st_mtime <= ACTIVE_WINDOW_SECONDS
    ]


def format_report(sessions, now=None):
    now = time.time() if now is None else now
    timestamp = datetime.fromtimestamp(now).strftime("%H:%M")
    lines = [f"Codex::: {timestamp} 進捗"]
    lines.extend(f"{item['label']}: {item['status']} — {item['update']}" for item in sessions)
    return "\n".join(lines)


def load_dotenv(path):
    values = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    except OSError:
        pass
    return values


def send_telegram(token, chat_id, text):
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status == 200


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions-root", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".openclaw" / ".env")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sessions = active_sessions(args.sessions_root)
    if not sessions:
        print("No active Codex sessions; no Telegram message sent.")
        return 0
    report = format_report(sessions)
    if args.dry_run:
        print(report)
        return 0

    env = {**load_dotenv(args.env_file), **os.environ}
    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_ALERT_CHAT_ID", "8547730585")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if not send_telegram(token, chat_id, report):
        raise RuntimeError("Telegram did not accept the progress report")
    print(f"Sent progress for {len(sessions)} active Codex session(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
