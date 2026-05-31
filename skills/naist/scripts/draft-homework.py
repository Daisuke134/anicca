#!/usr/bin/env python3
"""draft-homework.py — per-class homework drafter.

For each `bucket=homework` thread in today's triaged file, build a draft skeleton
under ~/.openclaw/workspace/naist/drafts/<class-slug>/<thread-id>.json and mark
slack_confirm_required=true. The agent layer fills the body_md and (optionally)
the qmd template body. send-as.py refuses to send anything that does not have a
matching ack file in confirms/.
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

DEFAULT_LANG = "ja"
DEFAULT_QMD = os.path.expanduser("~/anicca-project/docs/naistQmd/paper.qmd")


def load_classes(slug: str) -> dict[str, Any]:
    p = STATE_ROOT / slug / "classes.json"
    if not p.exists():
        return {"classes": {}}
    return json.loads(p.read_text())


def load_config(slug: str) -> dict[str, Any]:
    p = STATE_ROOT / slug / "config.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def class_for_thread(thread: dict[str, Any], classes: dict[str, Any]) -> str:
    subj = (thread.get("subject") or "").lower()
    for slug, cfg in (classes.get("classes") or {}).items():
        for kw in cfg.get("subject_keywords", []):
            if kw.lower() in subj:
                return slug
    return "general"


def build_skeleton(thread: dict[str, Any], class_slug: str, cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": thread["id"],
        "class_slug": class_slug,
        "from": cfg.get("naist_email", ""),
        "to": thread.get("from", ""),
        "subject": "Re: " + (thread.get("subject") or ""),
        "in_reply_to": thread.get("id"),
        "lang": cfg.get("reply_language", DEFAULT_LANG),
        "body_md": "<<AGENT FILLS THIS>>",
        "attachment_qmd": cfg.get("quarto_template", DEFAULT_QMD),
        "attachment_pdf": str(
            WORKSPACE / "homework" / class_slug / f"{thread['id']}-{dt.date.today().isoformat()}.pdf"
        ),
        "slack_confirm_required": True,  # ALWAYS True for homework, regardless of auto_confirm
        "auto_confirm_overridable": False,
        "created_at": dt.datetime.utcnow().isoformat() + "Z",
        "status": "pending_agent_fill",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

    if not SLUG:
        print("draft-homework: SLUG env required", file=sys.stderr)
        return 64

    today = dt.date.today().isoformat()
    triaged_path = WORKSPACE / f"triaged-{today}.json"
    if not triaged_path.exists():
        print(f"draft-homework[{SLUG}]: no triaged file for {today} — nothing to draft.")
        return 0

    triaged = json.loads(triaged_path.read_text())
    homework = [t for t in triaged if t.get("bucket") == "homework" and t.get("slug") == SLUG]
    if not homework:
        print(f"draft-homework[{SLUG}]: 0 homework threads — done.")
        return 0

    classes = load_classes(SLUG)
    config = load_config(SLUG)
    cfg_default = {
        "naist_email": config.get("naist_email", ""),
        "reply_language": config.get("reply_language", DEFAULT_LANG),
        "quarto_template": config.get("quarto_template", DEFAULT_QMD),
    }

    drafted = 0
    for t in homework:
        class_slug = class_for_thread(t, classes)
        merged = {**cfg_default, **(classes.get("classes", {}).get(class_slug, {}))}
        skeleton = build_skeleton(t, class_slug, merged)

        out_dir = WORKSPACE / "drafts" / class_slug
        out_path = out_dir / f"{t['id']}.json"
        if DRY_RUN or args.plan_only:
            print(f"draft-homework[{SLUG}][DRY_RUN]: would write {out_path}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2))
        drafted += 1

    print(f"draft-homework[{SLUG}]: prepared {drafted} draft skeletons (Slack-confirm required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
