#!/usr/bin/env python3
"""professor-mode.py — TA-style replies to professor-task threads with verified citations.

Reads professor-task threads from today's triaged file, builds a draft skeleton at
~/.openclaw/workspace/naist/drafts/professor/<thread-id>.json. The agent layer fills body_md.

Every citation in body_md is cross-checked against OpenAlex BEFORE the draft is approved
to send. The check is a HEAD on https://api.openalex.org/works/doi:<DOI> or works/<arXiv:ID>.
If any citation fails, the draft is marked status=citation_failed and Slack-flagged.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/naist"))
STATE_ROOT = Path(os.path.expanduser("~/.openclaw/state/naist"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SLUG = os.environ.get("SLUG", "")

DOI_RX = re.compile(r"\bdoi:\s*(10\.\d{4,9}/[^\s)\]]+)", re.I)
ARXIV_RX = re.compile(r"\barxiv:\s*(\d{4}\.\d{4,5})", re.I)


def openalex_check(ident: str, kind: str) -> bool:
    if DRY_RUN:
        return True  # don't call network in dry-run
    if kind == "doi":
        url = f"https://api.openalex.org/works/doi:{ident}"
    else:
        url = f"https://api.openalex.org/works/https://arxiv.org/abs/{ident}"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "openclaw-naist/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def verify_body(body: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for m in DOI_RX.finditer(body or ""):
        ident = m.group(1)
        if not openalex_check(ident, "doi"):
            failures.append(f"doi:{ident}")
    for m in ARXIV_RX.finditer(body or ""):
        ident = m.group(1)
        if not openalex_check(ident, "arxiv"):
            failures.append(f"arxiv:{ident}")
    return (len(failures) == 0), failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", help="path to a populated draft JSON to verify")
    ap.add_argument("--prepare", action="store_true", help="prepare skeletons from today's triaged")
    args = ap.parse_args()

    if args.draft:
        draft = json.loads(Path(args.draft).read_text())
        ok, fails = verify_body(draft.get("body_md", ""))
        if ok:
            draft["status"] = "citations_verified"
            print(f"professor-mode[verify]: OK for {args.draft}")
        else:
            draft["status"] = "citation_failed"
            draft["citation_failures"] = fails
            print(f"professor-mode[verify]: FAILED — {len(fails)} citations: {fails}")
        if DRY_RUN:
            print("[DRY_RUN] would update draft in place")
        else:
            Path(args.draft).write_text(json.dumps(draft, ensure_ascii=False, indent=2))
        return 0 if ok else 75

    if not SLUG:
        print("professor-mode: SLUG env required for prepare mode", file=sys.stderr)
        return 64

    today = dt.date.today().isoformat()
    triaged_path = WORKSPACE / f"triaged-{today}.json"
    if not triaged_path.exists():
        print(f"professor-mode[{SLUG}]: no triaged file for {today}.")
        return 0

    threads = json.loads(triaged_path.read_text())
    prof = [t for t in threads if t.get("bucket") == "professor-task" and t.get("slug") == SLUG]
    if not prof:
        print(f"professor-mode[{SLUG}]: 0 professor-task threads.")
        return 0

    out_dir = WORKSPACE / "drafts" / "professor"
    prepared = 0
    for t in prof:
        skeleton = {
            "thread_id": t["id"],
            "to": t.get("from"),
            "subject": "Re: " + (t.get("subject") or ""),
            "in_reply_to": t["id"],
            "body_md": "<<AGENT FILLS THIS — include DOI/arXiv refs in `doi:10.xxxx/...` or `arxiv:NNNN.NNNNN` form>>",
            "citation_policy": "openalex-verified",
            "status": "pending_agent_fill",
            "created_at": dt.datetime.utcnow().isoformat() + "Z",
        }
        out_path = out_dir / f"{t['id']}.json"
        if DRY_RUN:
            print(f"professor-mode[{SLUG}][DRY_RUN]: would write {out_path}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2))
        prepared += 1
    print(f"professor-mode[{SLUG}]: prepared {prepared} professor-task drafts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
