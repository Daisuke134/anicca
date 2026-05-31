#!/usr/bin/env python3
"""triage.py — classify forwarded NAIST mails into 6 buckets.

Reads:
  ~/.openclaw/workspace/naist/inbox-YYYY-MM-DD.json   (written by Gmail MCP search_threads in agentTurn)

Writes:
  ~/.openclaw/workspace/naist/triaged-YYYY-MM-DD.json

The agentTurn caller is expected to feed Gmail MCP search results into the inbox file
before invoking this script. In DRY_RUN mode (or when the inbox file is missing) we
synthesise a stub inbox so the cron exits cleanly.

Buckets: announcement / homework / question / ta-task / professor-task / bureaucracy
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/naist"))
STATE_ROOT = Path(os.path.expanduser("~/.openclaw/state/naist"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SLUG = os.environ.get("SLUG", "")

BUCKETS = (
    "announcement",
    "homework",
    "question",
    "ta-task",
    "professor-task",
    "bureaucracy",
)

# Lightweight rule sets. The agent layer can refine after; this is a fast pre-filter.
RX_ANN = re.compile(r"(お知らせ|notice|announcement|通知|bulletin)", re.I)
RX_HW = re.compile(r"(課題|提出|homework|assignment|期限|due\s+by|deadline|レポート|report)", re.I)
RX_BUR = re.compile(r"(健康診断|安全|safety|奨学金|scholarship|在留|visa|tuition|学費|納付)", re.I)
RX_TA = re.compile(r"\bTA\b|TA業務|grading|採点|teaching\s+assistant", re.I)
RX_QUESTION = re.compile(r"[?？]")


def load_profile(slug: str) -> dict[str, Any]:
    p = STATE_ROOT / slug / "profile.json"
    if p.exists():
        return json.loads(p.read_text())
    # legacy v1 fallback — synthesise a minimal profile
    legacy = {}
    em = STATE_ROOT / slug / "email_naist.txt"
    if em.exists():
        legacy["naist_email"] = em.read_text().strip()
    return {"advisors": [], "lab_members": [], "ta_coordinators": [], **legacy}


def classify(thread: dict[str, Any], profile: dict[str, Any]) -> str:
    sender = (thread.get("from") or "").lower()
    subject = thread.get("subject") or ""
    snippet = thread.get("snippet") or ""
    blob = f"{subject}\n{snippet}"

    if any(a.lower() in sender for a in profile.get("advisors", [])):
        return "professor-task"
    if RX_TA.search(blob) or any(t.lower() in sender for t in profile.get("ta_coordinators", [])):
        return "ta-task"
    if RX_BUR.search(blob):
        return "bureaucracy"
    if RX_HW.search(blob):
        return "homework"
    if any(p.lower() in sender for p in profile.get("lab_members", [])) and RX_QUESTION.search(blob):
        return "question"
    if RX_ANN.search(blob) or any(s in sender for s in ("staff@", "info@", "office@")):
        return "announcement"
    # fallback heuristic: institutional NAIST sender → announcement
    if "naist.jp" in sender:
        return "announcement"
    return "announcement"


def stub_inbox() -> list[dict[str, Any]]:
    return [
        {
            "id": "stub-1",
            "from": "staff@is.naist.jp",
            "subject": "[NAIST] 健康診断のお知らせ",
            "snippet": "5月15日に健康診断を実施します。受診票を持参してください。",
            "date": dt.datetime.utcnow().isoformat() + "Z",
        },
        {
            "id": "stub-2",
            "from": "prof.tanaka@is.naist.jp",
            "subject": "NLP 2026 課題3 提出について",
            "snippet": "課題3の提出期限は5月20日です。提出方法はmoodleで...",
            "date": dt.datetime.utcnow().isoformat() + "Z",
        },
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--rollup", choices=["24h", "7d"], default=None)
    ap.add_argument("--audit-deadlines", action="store_true")
    args = ap.parse_args()

    if not SLUG:
        print("triage: SLUG env required", file=sys.stderr)
        return 64

    today = dt.date.today().isoformat()
    inbox_path = WORKSPACE / f"inbox-{today}.json"
    triaged_path = WORKSPACE / f"triaged-{today}.json"

    if inbox_path.exists():
        raw = json.loads(inbox_path.read_text())
        # Accept both {"threads": [...]} envelope and bare list.
        threads = raw["threads"] if isinstance(raw, dict) and "threads" in raw else raw
    else:
        if DRY_RUN or args.plan_only:
            threads = stub_inbox()
        else:
            print(f"triage[{SLUG}]: no inbox file at {inbox_path} — agent should populate via Gmail MCP first.")
            return 0

    profile = load_profile(SLUG)
    counts = {b: 0 for b in BUCKETS}
    triaged: list[dict[str, Any]] = []
    for t in threads:
        bucket = classify(t, profile)
        counts[bucket] += 1
        triaged.append({**t, "bucket": bucket, "slug": SLUG})

    summary = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
    print(f"triage[{SLUG}]: {len(threads)} threads → {summary or 'none'}")

    if DRY_RUN or args.plan_only:
        print(f"triage[{SLUG}][DRY_RUN]: would write {triaged_path} ({len(triaged)} entries)")
    else:
        triaged_path.write_text(json.dumps(triaged, ensure_ascii=False, indent=2))
        print(f"triage[{SLUG}]: wrote {triaged_path}")

    if args.audit_deadlines:
        homework = [t for t in triaged if t["bucket"] == "homework"]
        print(f"triage[{SLUG}]: deadline-audit — {len(homework)} homework threads in window")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
