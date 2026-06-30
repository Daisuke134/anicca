"""bot2bot — gh issue-based AI-to-AI coordination (sprint-2).

PROP-B3-annotate (sprint-2 ships annotate-pr ONLY; auto-merge SCOPE-DEFERRED to sprint-3).
PROP-B4 (no human-touch in escalation labels).
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from lib._common import append_jsonl


_HUMAN_BODY_PHRASES = [
    "dais", "owner please", "human", "manual review",
    "please intervene", "please look at this", "needs attention",
    # FIND-013 fix: bypasses caught by lower() before substring match
    "human-in-the-loop", "humanintheloop", "@dais", "human required",
    "needs review by", "please review", "human approval", "ask the owner",
    "owner-only", "manual approval", "user input required",
]


def _gh_call(*args, **kw) -> str:
    """Default subprocess wrapper; tests monkeypatch via 'lib.bot2bot._gh_call'."""
    cmd = ["gh"] + list(args)
    try:
        out = subprocess.check_output(cmd, timeout=30, stderr=subprocess.DEVNULL)
        return out.decode("utf-8")
    except Exception:
        return ""


def post(*, slot: str, kind: str, body_text: str) -> str:
    """REQ-B1: create gh issue with label=bot2bot-<kind>. PROP-B4 enforces no
    human-targeted body even with 'escalation' kind."""
    if kind == "escalation":
        lower = body_text.lower()
        for phrase in _HUMAN_BODY_PHRASES:
            if phrase in lower:
                raise ValueError(
                    f"PROP-B4 violation: 'escalation' label MUST NOT carry human-targeted "
                    f"body (phrase {phrase!r} detected). REQ-J8."
                )

    label = f"bot2bot-{kind}"
    title = f"[bot2bot][{slot}][{kind}]"
    url = _gh_call("issue", "create", "--label", label, "--title", title, "--body", body_text)
    url = url.strip() or f"local://no-gh"

    append_jsonl(Path.home() / "loops" / slot / "bot2bot-sent.jsonl", {
        "ts": int(time.time()), "slot": slot, "kind": kind, "issue_url": url,
    })
    return url


def poll(*, slot: str) -> list[dict]:
    """REQ-B2 (FIND-008 fix): fetch ALL bot2bot-* labels (not hardcoded to one),
    filter by slot via the title's [bot2bot][<slot>][<kind>] prefix, empty list
    if none, NEVER crashes.
    """
    out = _gh_call(
        "issue", "list",
        "--search", "label:bot2bot-review-requested label:bot2bot-opinion-requested "
                    "label:bot2bot-escalation label:bot2bot-pr-mentioned",
        "--state", "open", "--json", "url,title,body,createdAt",
    )
    if not out.strip() or out.strip() == "[]":
        return []
    try:
        raw = json.loads(out)
    except json.JSONDecodeError:
        return []
    parsed = [parse_bot2bot_issue(j) for j in raw]
    # Filter by slot
    return [t for t in parsed if t.get("slot") == slot]


def parse_bot2bot_issue(gh_json: dict) -> dict:
    """Parse a gh issue payload into a TaskRow."""
    title = gh_json.get("title", "")
    m = re.match(r"\[bot2bot\]\[([^\]]+)\]\[([^\]]+)\]", title)
    slot = m.group(1) if m else "unknown"
    kind = m.group(2) if m else "unknown"
    return {
        "issue_url": gh_json.get("url"),
        "slot": slot,
        "kind": kind,
        "body": gh_json.get("body", ""),
        "ts_created": gh_json.get("createdAt"),
    }


def annotate_pr(*, slot: str, pr_number: int, verdict: dict) -> None:
    """REQ-B3 sprint-2: COMMENT only. Auto-merge is SCOPE-DEFERRED to sprint-3.
    PROP-B3-annotate asserts this function never calls 'gh pr merge'.
    """
    body = json.dumps({"slot": slot, "verdict": verdict, "ts": int(time.time())})
    _gh_call("pr", "comment", str(pr_number), "--body", body)
    # NO merge call here. PROP-B3-annotate enforces this.
