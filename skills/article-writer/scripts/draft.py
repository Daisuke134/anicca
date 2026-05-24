#!/usr/bin/env python3
"""
draft.py — Pick a subject and emit EN + JA draft skeletons.

Subject sourcing (weighted random):
  40% — today's diary at ~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md
  30% — codebase: most-changed file in ~/anicca-project (git log last 7 days)
  30% — community/news: pull from ~/.openclaw/workspace/article-writer/backlog.md

Output:
  ~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD/{en,ja}.md
  Both drafts share the same subject; EN target ~1500 words, JA mirrors structure.

Notes:
  - This is a SKELETON generator. It outputs a frontmatter + 5-section outline.
  - Anicca then expands each section. We do NOT call an LLM directly here.
  - DRY_RUN: ARTICLE_DRY_RUN=true emits to /tmp instead of workspace.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "article-writer"
DIARY_DIR = Path.home() / ".openclaw" / "workspace" / "daily-memory"
REPO = Path(os.environ.get("BIP_REPO_PATH", str(Path.home() / "anicca-project")))
DRY_RUN = os.environ.get("ARTICLE_DRY_RUN", "false").lower() == "true"
WORD_TARGET = int(os.environ.get("ARTICLE_WORD_TARGET", "1500"))


def pick_source() -> tuple[str, str]:
    """Returns (source_kind, raw_text)."""
    r = random.random()
    today = date.today().strftime("%Y-%m-%d")
    if r < 0.40:
        f = DIARY_DIR / f"diary-{today}.md"
        if f.exists():
            return "diary", f.read_text()
    if r < 0.70:
        try:
            out = subprocess.run(
                ["git", "log", "--since=7.days", "--name-only", "--pretty=format:"],
                cwd=REPO, capture_output=True, text=True, timeout=10,
            )
            files = [l.strip() for l in out.stdout.splitlines() if l.strip()]
            if files:
                top = max(set(files), key=files.count)
                return "codebase", f"Most-changed file in last 7d: {top} ({files.count(top)} commits)"
        except Exception:
            pass
    bl = WORKSPACE / "backlog.md"
    if bl.exists():
        items = [l.strip() for l in bl.read_text().splitlines() if l.strip().startswith("- ")]
        if items:
            return "backlog", random.choice(items)
    # ultimate fallback
    return "fallback", "Reflections on building Anicca, day-by-day."


def is_weekend() -> bool:
    """Sat/Sun → switch to weekly-summary cadence."""
    return datetime.now().weekday() >= 5


def make_skeleton(lang: str, source_kind: str, raw: str) -> str:
    title_hint = raw.splitlines()[0][:80] if raw else "Today"
    weekend = is_weekend()
    cadence = "weekly-summary" if weekend else "daily-deep-dive"

    if lang == "en":
        fm = (
            "---\n"
            f"title: \"{title_hint}\"\n"
            "published: false\n"
            "tags: agi, opensource, ai, automation\n"
            f"date: {date.today().isoformat()}\n"
            "---\n\n"
        )
        body = (
            f"<!-- source: {source_kind} | cadence: {cadence} | target_words: {WORD_TARGET} -->\n\n"
            "## Hook\n\n[2-3 sentences. Specific outcome or counterintuitive observation.]\n\n"
            "## Context\n\n[Why this matters today. Tie to today's diary / commit / news.]\n\n"
            "## What I Tried\n\n[Concrete steps. Code snippet if applicable.]\n\n"
            "## What Broke / What Worked\n\n[Honest. Specific numbers if possible.]\n\n"
            "## Takeaway\n\n[1 sentence claim. 1 sentence what I'd do differently.]\n\n"
            "---\n\n"
            f"_Source material:_\n\n```\n{raw[:600]}\n```\n"
        )
        return fm + body

    # ja
    fm = (
        "---\n"
        f"title: \"{title_hint}\"\n"
        "emoji: \"🐢\"\n"
        "type: \"idea\"\n"
        "topics: [\"agi\", \"opensource\", \"ai\", \"automation\"]\n"
        "published: true\n"
        "---\n\n"
    )
    body = (
        f"<!-- source: {source_kind} | cadence: {cadence} | target_words: {WORD_TARGET} -->\n\n"
        "## はじめに\n\n[2-3文。具体的な結果か、反直感的な観察。]\n\n"
        "## 背景\n\n[なぜ今日それを書くのか。日記・コミット・ニュースに紐づける。]\n\n"
        "## 何を試したか\n\n[具体的な手順。必要ならコード片。]\n\n"
        "## 何が壊れて、何が機能したか\n\n[正直に。可能なら数字。]\n\n"
        "## 学び\n\n[主張1文。次回どうするか1文。]\n\n"
        "---\n\n"
        f"_元ネタ:_\n\n```\n{raw[:600]}\n```\n"
    )
    return fm + body


def main() -> int:
    today = date.today().strftime("%Y-%m-%d")
    out_root = (Path("/tmp/article-writer-dryrun") if DRY_RUN else WORKSPACE) / "drafts" / today
    out_root.mkdir(parents=True, exist_ok=True)

    src_kind, raw = pick_source()
    en = make_skeleton("en", src_kind, raw)
    ja = make_skeleton("ja", src_kind, raw)

    (out_root / "en.md").write_text(en, encoding="utf-8")
    (out_root / "ja.md").write_text(ja, encoding="utf-8")

    meta = {
        "date": today,
        "source": src_kind,
        "raw_preview": raw[:200],
        "weekend_cadence": is_weekend(),
        "word_target": WORD_TARGET,
        "dry_run": DRY_RUN,
    }
    (out_root / "_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"\nDrafts: {out_root}/en.md, {out_root}/ja.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
