#!/usr/bin/env python3
"""research-proposal-gen.py — generate a 科研費 proposal PDF via Quarto.

Reads ~/.openclaw/state/naist/<slug>/research-profile.json. Renders into
~/.openclaw/workspace/naist/<slug>/proposals/<ymd>/proposal.pdf using a
KAKENHI-styled Quarto template. Posts a Slack note with the PDF path.

If research-profile.json has any "TBD" field in {topic, method,
preliminary_results}, the script aborts with a Slack warning so the user
fills the gaps before the proposal goes out.

Auto-submit per v1.5: this only generates the PDF — the actual portal
submission happens in funds-apply.py.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SLUG = os.environ.get("SLUG", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "naist"
STATE_ROOT = Path.home() / ".openclaw" / "state" / "naist"


def fail(msg: str) -> None:
    print(f"research-proposal-gen[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def slack_post(text: str) -> None:
    if DRY_RUN or not SLACK_TOKEN:
        print(f"[DRY] Slack: {text[:160]}")
        return
    ch_path = STATE_ROOT / SLUG / "slack_channel.txt"
    channel = ch_path.read_text().strip() if ch_path.exists() else "{{profile.channels.reportChannel}}"
    import urllib.request
    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception as e:
        print(f"slack_post error: {e}", file=sys.stderr)


def main() -> int:
    if not SLUG:
        fail("SLUG env required")
    profile_path = STATE_ROOT / SLUG / "research-profile.json"
    if not profile_path.exists():
        slack_post(f":warning: research-proposal-gen[{SLUG}]: research-profile.json missing")
        return 0
    profile = json.loads(profile_path.read_text())
    missing = [k for k in ("topic", "method", "preliminary_results")
               if not profile.get(k) or "TBD" in str(profile[k]).upper()]
    if missing:
        slack_post(
            f":warning: research-proposal-gen[{SLUG}]: blocked — fill these in research-profile.json: {', '.join(missing)}"
        )
        print(f"research-proposal-gen[{SLUG}]: blocked on {missing}")
        return 0

    if not shutil.which("quarto"):
        fail("quarto CLI not installed (`brew install --cask quarto`)")

    today = date.today().isoformat()
    out_dir = WORKSPACE / SLUG / "proposals" / today
    out_dir.mkdir(parents=True, exist_ok=True)

    keywords = profile.get("research_keywords") or []
    qmd = out_dir / "proposal.qmd"
    qmd.write_text(
        f"""---
title: "{profile.get('topic','')}"
author: "{profile.get('user_full_name_kanji', SLUG)}"
date: "{today}"
format: typst
---

# 1. 研究目的（Research Purpose）

{profile.get('topic','')}

# 2. 研究方法（Research Method）

{profile.get('method','')}

# 3. 予備実験結果（Preliminary Results）

{profile.get('preliminary_results','')}

# 4. キーワード（Keywords）

{', '.join(keywords) if keywords else 'TBD'}

# 5. 関連研究（Related Work）

(papers-suggest 履歴から自動引用 — TODO Phase 2)

# 6. 予算計画（Budget）

(funds-apply の funder テンプレに合わせて自動生成 — TODO Phase 2)

# 7. 連絡先（Contact）

{profile.get('user_full_name_kanji','')}, {profile.get('lab','TBD')}, {{profile.education.institution}}
""",
        encoding="utf-8",
    )

    # Quarto + Typst engine renders PDF without LaTeX (built-in to quarto 1.4+).
    cmd = ["quarto", "render", str(qmd)]
    print(f"running: {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(out_dir), capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        slack_post(
            f":x: research-proposal-gen[{SLUG}]: typst render failed ({r.returncode}). "
            f"stderr: {(r.stderr or '')[:300]}"
        )
        return 1

    out_pdf = out_dir / "proposal.pdf"
    if not out_pdf.exists():
        slack_post(
            f":x: research-proposal-gen[{SLUG}]: render returned 0 but no proposal.pdf at {out_pdf}"
        )
        return 1

    slack_post(
        f":memo: research-proposal-gen[{SLUG}]: rendered (Typst). `{out_pdf}` ready for funds-apply."
    )
    print(f"research-proposal-gen[{SLUG}]: wrote {out_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
