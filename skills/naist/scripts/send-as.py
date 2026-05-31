#!/usr/bin/env python3
"""send-as.py — wrapper around Gmail "Send mail as" for NAIST replies.

The agent never touches NAIST SMTP. This script:
  1. Loads a draft from ~/.openclaw/workspace/naist/drafts/<class>/<thread>.json
  2. Verifies a matching ack file exists at confirms/<thread>.ack (homework HARD-GATE)
  3. Emits a JSON envelope to stdout that the agent layer feeds into Gmail MCP send
     (with `from: <naist email>` so Gmail uses the configured "Send mail as" alias)
  4. Appends an entry to sent.json

In DRY_RUN mode it stops before step 3 and prints the planned envelope.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/naist"))
CONFIRMS = WORKSPACE / "confirms"
SENT_LEDGER = WORKSPACE / "sent.json"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def append_ledger(entry: dict) -> None:
    SENT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if SENT_LEDGER.exists():
        try:
            items = json.loads(SENT_LEDGER.read_text())
        except json.JSONDecodeError:
            items = []
    items.append(entry)
    SENT_LEDGER.write_text(json.dumps(items, ensure_ascii=False, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", help="path to draft JSON")
    ap.add_argument("--confirm", action="store_true", help="record a Slack ack reaction")
    args = ap.parse_args()

    if args.confirm:
        thread_ts = os.environ.get("THREAD_TS", "")
        reaction = os.environ.get("REACTION", "")
        if not thread_ts or not reaction:
            print("send-as confirm: THREAD_TS and REACTION required", file=sys.stderr)
            return 64
        CONFIRMS.mkdir(parents=True, exist_ok=True)
        suffix = ".ack" if reaction in ("+1", "👍") else ".discard"
        (CONFIRMS / f"{thread_ts}{suffix}").write_text(
            json.dumps({"ts": thread_ts, "reaction": reaction, "at": dt.datetime.utcnow().isoformat() + "Z"})
        )
        print(f"send-as[confirm]: recorded {reaction} for {thread_ts}")
        return 0

    if not args.draft:
        print("send-as: --draft <path> required (or --confirm)", file=sys.stderr)
        return 64

    draft_path = Path(args.draft)
    if not draft_path.exists():
        print(f"send-as: draft not found: {draft_path}", file=sys.stderr)
        return 66
    draft = json.loads(draft_path.read_text())

    # HARD GATE: homework class always requires ack
    thread_id = draft.get("thread_id", "")
    if draft.get("slack_confirm_required"):
        ack_path = CONFIRMS / f"{thread_id}.ack"
        if not ack_path.exists():
            print(f"send-as[ABORT]: no ack at {ack_path} — homework must be Slack-confirmed first.")
            return 75

    if "<<AGENT FILLS THIS>>" in (draft.get("body_md") or ""):
        print("send-as[ABORT]: body_md still placeholder — agent must fill before send.")
        return 76

    envelope = {
        "from": draft["from"],
        "to": draft["to"],
        "subject": draft["subject"],
        "in_reply_to": draft["in_reply_to"],
        "body_md": draft["body_md"],
        "attachments": [draft["attachment_pdf"]] if draft.get("attachment_pdf") and Path(draft["attachment_pdf"]).exists() else [],
        "alias": draft["from"],  # Gmail "Send mail as" alias
    }

    if DRY_RUN:
        print("send-as[DRY_RUN]: would invoke gmail.send with:")
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(envelope, ensure_ascii=False))
    append_ledger({
        "thread_id": thread_id,
        "class_slug": draft.get("class_slug"),
        "to": envelope["to"],
        "subject": envelope["subject"],
        "sent_at": dt.datetime.utcnow().isoformat() + "Z",
    })
    print(f"send-as: emitted envelope for {thread_id} → {envelope['to']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
