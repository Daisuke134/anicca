#!/usr/bin/env python3
"""draft-grant.py — bridge from auto-research project → apply-to-funder skill.

Picks an open funder spec under ~/.openclaw/skills/apply-to-funder/funders/ and queues
a draft-request for it, populated with the most-recent paper draft for this project.

This script does NOT submit anything. It writes a payload that apply-to-funder's own
agentTurn cron will pick up.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/auto-research"))
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
APPLY_TO_FUNDER = Path(os.path.expanduser("~/.openclaw/skills/apply-to-funder"))


def latest_paper(pid: str) -> Path | None:
    base = WORKSPACE / "papers" / pid
    if not base.exists():
        return None
    days = sorted([p for p in base.iterdir() if p.is_dir()], reverse=True)
    for d in days:
        md = d / "draft.md"
        if md.exists():
            return md
    return None


def pick_funder() -> str | None:
    funders_dir = APPLY_TO_FUNDER / "funders"
    if not funders_dir.exists():
        return None
    candidates = sorted(funders_dir.glob("*.json"))
    return candidates[0].stem if candidates else None


def main(project: dict) -> int:
    pid = project["id"]
    today = dt.date.today().isoformat()
    out_dir = WORKSPACE / "grants" / pid / today
    out_dir.mkdir(parents=True, exist_ok=True)

    paper = latest_paper(pid)
    funder = pick_funder() or "anthropic-builder-grants"

    payload = {
        "project_id": pid,
        "funder": funder,
        "draft_md": str(paper) if paper else None,
        "queued_at": dt.datetime.utcnow().isoformat() + "Z",
        "next_action": f"apply-to-funder MODE=prepare bash scripts/run.sh --funder {funder}",
    }
    out_path = out_dir / "submission.json"

    if DRY_RUN:
        print(f"draft-grant[{pid}][DRY_RUN]: would queue funder={funder}, paper={paper}")
        print(f"draft-grant[{pid}][DRY_RUN]: payload preview:")
        print(json.dumps(payload, indent=2))
        out_path.write_text(json.dumps({**payload, "stub": True}, indent=2))
        return 0

    out_path.write_text(json.dumps(payload, indent=2))
    print(f"draft-grant[{pid}]: queued funder={funder} → {out_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: draft-grant.py <project-json>", file=sys.stderr); raise SystemExit(64)
    blob = json.loads(sys.argv[1])
    raise SystemExit(main(blob["project"]))
