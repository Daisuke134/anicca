#!/usr/bin/env python3
"""daily-report — send composed email via AgentMail.

Reads body from stdin (the compose.py output: SUBJECT: line + BODY-START/END).
Sends via AgentMail Python SDK using AGENTMAIL_API_KEY + AGENTMAIL_INBOX_ID.
Recipients come from ANICCA_REPORT_TO (comma-separated) or --to override.

Prints a JSON trace to stdout: {ok, recipients, subject, body_chars, message_id|null, error|null}.
Always exits 0 (the trace says ok=false on failure; cron treats it as silent).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

try:
    from agentmail import AgentMail
except ImportError as e:
    print(json.dumps({"ok": False, "error": f"agentmail not installed: {e}"}))
    sys.exit(0)


def parse_compose_stream(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    subject = ""
    body_lines: list[str] = []
    state = "header"
    for ln in lines:
        if state == "header":
            if ln.startswith("SUBJECT: "):
                subject = ln[len("SUBJECT: "):]
            elif ln == "BODY-START":
                state = "body"
        elif state == "body":
            if ln == "BODY-END":
                state = "done"
                break
            body_lines.append(ln)
    return subject, "\n".join(body_lines)


def load_env_file(path: Path) -> None:
    """Best-effort .env loader; preserves existing os.environ values."""
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--to", default="", help="comma-separated override")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    load_env_file(Path.home() / ".hermes" / ".env")
    api_key = os.environ.get("AGENTMAIL_API_KEY", "")
    inbox_id = os.environ.get("AGENTMAIL_INBOX_ID", "")
    default_to = os.environ.get("ANICCA_REPORT_TO", "")

    text = sys.stdin.read()
    subject, body = parse_compose_stream(text)

    recipients_raw = args.to or default_to
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    trace = {
        "ok": False,
        "recipients": recipients,
        "subject": subject,
        "body_chars": len(body),
        "message_id": None,
        "error": None,
    }

    if args.dry_run:
        trace["ok"] = True
        trace["error"] = "dry-run"
        print(json.dumps(trace, ensure_ascii=False))
        return 0

    if not api_key or not inbox_id:
        trace["error"] = "missing AGENTMAIL_API_KEY or AGENTMAIL_INBOX_ID"
        print(json.dumps(trace, ensure_ascii=False))
        return 0
    if not recipients:
        trace["error"] = "no recipients (ANICCA_REPORT_TO empty and --to not given)"
        print(json.dumps(trace, ensure_ascii=False))
        return 0
    if not subject or not body:
        trace["error"] = "stdin did not contain SUBJECT: / BODY-START / BODY-END markers"
        print(json.dumps(trace, ensure_ascii=False))
        return 0

    try:
        client = AgentMail(api_key=api_key)
        # X-Anicca-Origin header lets recipients (and tests) distinguish the
        # Hermes-native send from the legacy OpenClaw anicca-report send that
        # still fires at 18:00 JST until LAUNCH-GATE #341 retires it.
        resp = client.inboxes.messages.send(
            inbox_id=inbox_id,
            to=recipients,
            subject=subject,
            text=body,
            headers={"X-Anicca-Origin": "hermes-genesis"},
        )
        trace["ok"] = True
        trace["message_id"] = getattr(resp, "message_id", None) or getattr(resp, "id", None)
    except Exception as e:  # noqa: BLE001 — keep cron silent
        trace["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    # Critical-alert path: if the send failed, write a severity=critical row
    # to ~/.hermes/state/daily-report-alerts.jsonl so Done condition #7 (>=7
    # consecutive successes + zero critical alerts) can detect it. Exit code
    # stays 0 so the cron job survives, but #330 cannot close until the
    # alert log stays clean for 7 days.
    if not trace["ok"]:
        try:
            from datetime import datetime, timezone
            alert_log = Path.home() / ".hermes" / "state" / "daily-report-alerts.jsonl"
            alert_log.parent.mkdir(parents=True, exist_ok=True)
            alert = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "severity": "critical",
                "source": "daily-report.send",
                "error": trace["error"],
                "recipients": recipients,
                "subject": subject,
            }
            with alert_log.open("a") as fh:
                fh.write(json.dumps(alert, ensure_ascii=False) + "\n")
        except Exception as alert_err:  # noqa: BLE001
            # Surface to the trace so daily-report.sh sees it, but never raise.
            trace["alert_log_error"] = f"{type(alert_err).__name__}: {str(alert_err)[:120]}"

    print(json.dumps(trace, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
