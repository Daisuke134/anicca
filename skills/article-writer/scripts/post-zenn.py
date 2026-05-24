#!/usr/bin/env python3
"""
post-zenn.py — Commit a Zenn article to the user's zenn-content fork and push.

Reads:  ~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD/ja.md
Repo:   ~/.openclaw/workspace/zenn-articles/  (or env ZENN_REPO_PATH)
SSH:    GIT_SSH_COMMAND="ssh -i $ZENN_SSH_KEY"

The frontmatter must include `published: true` (set by draft.py). This script
copies the file into `articles/<slug>.md`, commits, and pushes to origin.

Env:
  ZENN_REPO_PATH     default ~/.openclaw/workspace/zenn-articles
  ZENN_SSH_KEY       default ~/.ssh/id_ed25519
  ARTICLE_DRY_RUN    "true" → no commit/push
  ARTICLE_DATE       override target draft date
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "article-writer"
PUBLISHED = WORKSPACE / "published.json"
LOG_DIR = Path.home() / ".openclaw" / "logs" / "article-writer"

ZENN_REPO = Path(os.environ.get("ZENN_REPO_PATH", str(Path.home() / ".openclaw" / "workspace" / "zenn-articles")))
SSH_KEY = os.environ.get("ZENN_SSH_KEY", str(Path.home() / ".ssh" / "id_ed25519"))
DRY_RUN = os.environ.get("ARTICLE_DRY_RUN", "false").lower() == "true"


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with (LOG_DIR / f"post-zenn_{date.today():%Y-%m-%d}.log").open("a") as fh:
        fh.write(line + "\n")


def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9一-龥ぁ-んァ-ヴ\- ]+", "", s)
    s = re.sub(r"\s+", "-", s)
    return (s or "anicca-day")[:60]


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes"
    return subprocess.run(["git"] + args, cwd=ZENN_REPO, env=env, capture_output=True, text=True)


def main() -> int:
    target = os.environ.get("ARTICLE_DATE", date.today().isoformat())
    src = WORKSPACE / "drafts" / target / "ja.md"
    if not src.exists():
        log(f"ERROR: draft not found: {src}")
        return 2

    text = src.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    title = "anicca-day"
    if m:
        for line in m.group(1).splitlines():
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"')
    slug = f"{target}-{slugify(title)}"
    rel_path = Path("articles") / f"{slug}.md"

    log(f"target_date={target} slug={slug} dry_run={DRY_RUN}")

    if DRY_RUN:
        log(f"[DRY_RUN] would copy {src} → {ZENN_REPO}/{rel_path}, commit + push")
        log(f"[DRY_RUN] zenn_repo={ZENN_REPO} ssh_key={SSH_KEY}")
        print(json.dumps({"dry_run": True, "slug": slug, "rel_path": str(rel_path)}, indent=2))
        return 0

    if not ZENN_REPO.exists():
        log(f"ERROR: zenn repo not found: {ZENN_REPO}")
        return 3

    dest = ZENN_REPO / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)

    add = run_git(["add", str(rel_path)])
    if add.returncode != 0:
        log(f"git add failed: {add.stderr}")
        return 4
    cm = run_git(["commit", "-m", f"article: {slug}"])
    if cm.returncode != 0 and "nothing to commit" not in (cm.stdout + cm.stderr).lower():
        log(f"git commit failed: {cm.stderr}")
        return 5
    push = run_git(["push", "origin", "HEAD"])
    if push.returncode != 0:
        log(f"git push failed: {push.stderr}")
        return 6

    url = f"https://zenn.dev/your-handle/articles/{slug}"
    log(f"OK pushed: {url}")
    history = []
    if PUBLISHED.exists():
        try:
            history = json.loads(PUBLISHED.read_text())
        except Exception:
            history = []
    history.append({
        "date": target, "platform": "zenn", "title": title, "url": url, "slug": slug,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    PUBLISHED.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    print(json.dumps({"url": url, "slug": slug}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
