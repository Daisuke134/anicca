#!/usr/bin/env python3
"""Enrich gog gmail search results with subject/from/snippet/body + we_replied flag."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

GOG = "/opt/homebrew/bin/gog"


def fetch(account: str, msg_id: str) -> dict:
    try:
        out = subprocess.run(
            [GOG, "-a", account, "gmail", "get", msg_id, "--json"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode != 0:
            return {}
        return json.loads(out.stdout or "{}")
    except Exception:
        return {}


def main():
    raw_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    account = sys.argv[3]
    state_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    state = {}
    if state_path and state_path.exists():
        state = json.loads(state_path.read_text())
    replied = set(state.get("replied", []))

    raw = json.loads(raw_path.read_text()) if raw_path.exists() else []
    enriched = []
    for row in raw:
        # gog gmail search returns thread-like rows with id, subject, from, snippet, thread_id ...
        msg_id = row.get("id") or row.get("message_id") or ""
        tid = row.get("thread_id") or row.get("threadId") or msg_id
        full = fetch(account, msg_id) if msg_id else {}
        body = (full.get("body_plain") or full.get("body") or full.get("snippet") or row.get("snippet") or "")[:5000]
        labels = full.get("label_ids") or row.get("label_ids") or []
        we_replied = tid in replied or "SENT" in labels
        enriched.append({
            "message_id": msg_id,
            "latest_message_id": msg_id,
            "thread_id": tid,
            "from": row.get("from") or full.get("from") or "",
            "subject": row.get("subject") or full.get("subject") or "",
            "snippet": row.get("snippet") or full.get("snippet") or "",
            "body": body,
            "labels": labels,
            "we_replied": we_replied,
        })
    out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
    print(json.dumps({"enriched": len(enriched)}))


if __name__ == "__main__":
    main()
