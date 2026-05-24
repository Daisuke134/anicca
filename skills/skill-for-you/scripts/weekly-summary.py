#!/usr/bin/env python3
"""
weekly-summary.py — every Sunday 09:00 JST.

Counts the past 7 days of recommendations + installed.json actions and posts
a single Slack message:

  📊 skill-for-you weekly  (2026-W19)
  Recommended N skills.  Installed M.  Valuable K (≥3 triggers).
  Top installed:
    - <slug>  (5 triggers)
    - <slug>  (4 triggers)

A skill is "valuable" if `installed.json[slug].triggered_count >= 3`.
The reaction handler (separate, not in this skill's scope) is expected to
increment `triggered_count` whenever the user actually invokes the installed
skill — for now, this script just reports what's there.

Output:
  ~/.openclaw/workspace/skill-for-you/weekly-YYYY-WW.json
"""

from __future__ import annotations

import json
import os
import sys
import datetime as dt
import urllib.request
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
WORKSPACE = HOME / ".openclaw" / "workspace" / "skill-for-you"
INSTALLED_PATH = WORKSPACE / "installed.json"

DRY_RUN = os.environ.get("SKILL_FOR_YOU_DRY_RUN", "").strip() not in ("", "0", "false", "False")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "{{profile.channels.reportChannel}}")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

TODAY = dt.date.today()
ISO_YEAR, ISO_WEEK, _ = TODAY.isocalendar()
WEEK_LABEL = f"{ISO_YEAR}-W{ISO_WEEK:02d}"


def collect_week():
    rec_paths = []
    inst_paths = []
    for delta in range(7):
        d = TODAY - dt.timedelta(days=delta)
        rp = WORKSPACE / f"recommendations-{d.isoformat()}.json"
        if rp.exists():
            rec_paths.append(rp)

    state = {}
    if INSTALLED_PATH.exists():
        try:
            state = json.loads(INSTALLED_PATH.read_text())
        except Exception:
            state = {}

    recommended = 0
    distinct_slugs = set()
    for rp in rec_paths:
        try:
            blob = json.loads(rp.read_text())
        except Exception:
            continue
        for p in blob.get("picks") or []:
            recommended += 1
            distinct_slugs.add(p.get("slug"))

    week_start = (TODAY - dt.timedelta(days=6)).isoformat()
    installed_this_week = []
    valuable = []
    for slug, s in state.items():
        if not isinstance(s, dict):
            continue
        action = s.get("action")
        ts = s.get("ts", "")
        try:
            t = dt.datetime.fromisoformat(ts).date().isoformat()
        except Exception:
            t = ""
        if action == "install" and t and t >= week_start:
            installed_this_week.append(slug)
        if int(s.get("triggered_count") or 0) >= 3:
            valuable.append((slug, int(s["triggered_count"])))

    valuable.sort(key=lambda x: x[1], reverse=True)
    return {
        "week": WEEK_LABEL,
        "recommended": recommended,
        "distinct_recommended": len(distinct_slugs),
        "installed_this_week": installed_this_week,
        "installed_count": len(installed_this_week),
        "valuable": [{"slug": s, "triggered_count": c} for s, c in valuable],
    }


def slack_post(text: str):
    if DRY_RUN or not SLACK_TOKEN:
        return False, "DRY_RUN or no token"
    body = json.dumps({"channel": SLACK_CHANNEL, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok", False), data.get("ts", "")
    except Exception as e:
        return False, f"slack failed: {e}"


def main() -> int:
    summary = collect_week()
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    out_path = WORKSPACE / f"weekly-{summary['week']}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    lines = [
        f"📊 *skill-for-you weekly* ({summary['week']})",
        f"Recommended {summary['recommended']} skills "
        f"({summary['distinct_recommended']} distinct).  "
        f"Installed {summary['installed_count']}.  "
        f"Valuable {len(summary['valuable'])} (≥3 triggers).",
    ]
    if summary["valuable"]:
        lines.append("Top valuable:")
        for v in summary["valuable"][:5]:
            lines.append(f"  • `{v['slug']}` — {v['triggered_count']} triggers")
    if summary["installed_this_week"]:
        lines.append("Installed this week:")
        for s in summary["installed_this_week"]:
            lines.append(f"  • `{s}`")
    text = "\n".join(lines)

    posted, status = slack_post(text)
    sys.stderr.write(
        f"[weekly-summary] wrote {out_path}  posted={posted}  status={status}  "
        f"dry_run={DRY_RUN}\n"
    )
    if not posted:
        sys.stderr.write("--- preview ---\n" + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
