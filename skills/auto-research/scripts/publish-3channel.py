#!/usr/bin/env python3
"""publish-3channel.py — publish today's paper draft to:
  1. aniccaai.com/blog/<slug> (Next.js MDX page committed to apps/landing repo)
  2. note.com (via existing auto-article-poster — separate skill)
  3. X long-form (Postiz to @aniccaen as a thread, NOT Articles which needs premium)

Reads ~/.openclaw/workspace/auto-research/papers/<project>/<date>.md and
its .meta.json. Writes:
  - apps/landing/data/research/<slug>.json (read by [slug]/page.tsx)
  - workspace/auto-research/published/<date>-<slug>.json (publish ledger)

If --skip-channel x|note|blog is passed, that channel is skipped.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/auto-research"))
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
LANDING_REPO = Path(os.path.expanduser("~/anicca-project/apps/landing"))
POSTIZ_KEY = os.environ.get("POSTIZ_API_KEY", "")
POSTIZ_X_INTEGRATION_EN = (
    os.environ.get("POSTIZ_X_INTEGRATION_ID")
    or os.environ.get("POSTIZ_X_INTEGRATION")
    or os.environ.get("POSTIZ_X_INTEGRATION_EN")
    or ""
)
SLACK_CHANNEL = "{{profile.channels.reportChannel}}"


def slack_post(text: str) -> None:
    if DRY_RUN or not SLACK_TOKEN:
        print(f"[DRY] Slack: {text[:200]}")
        return
    payload = json.dumps({"channel": SLACK_CHANNEL, "text": text}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception as e:
        print(f"slack error: {e}", file=sys.stderr)


def publish_blog(meta: dict, md: str) -> dict:
    """Commit data file to apps/landing/data/research/<slug>.json."""
    slug = meta["slug"]
    data_dir = LANDING_REPO / "data" / "research"
    data_dir.mkdir(parents=True, exist_ok=True)
    out = data_dir / f"{slug}.json"
    out.write_text(json.dumps({
        "slug": slug,
        "title": meta["title"],
        "date": meta["date"],
        "project": meta["project"],
        "n_papers_cited": meta["n_papers_cited"],
        "word_count": meta["word_count_approx"],
        "markdown": md,
    }, ensure_ascii=False, indent=2))

    if DRY_RUN:
        return {"channel": "blog", "url": None, "dry_run": True, "data_file": str(out)}

    # git commit + push (apps/landing is in anicca-project monorepo)
    repo_root = LANDING_REPO.parent.parent
    rel = out.relative_to(repo_root)
    subprocess.run(["git", "-C", str(repo_root), "add", str(rel)], check=False, capture_output=True)
    cmsg = f"research: publish {meta['title']} ({slug})"
    subprocess.run(
        ["git", "-C", str(repo_root), "-c", "credential.helper=", "commit", "-m", cmsg],
        check=False, capture_output=True,
    )
    push = subprocess.run(
        ["git", "-C", str(repo_root), "-c", "credential.helper=", "push", "origin", "HEAD"],
        capture_output=True, text=True, timeout=120,
    )
    url = f"https://aniccaai.com/blog/{slug}"
    return {
        "channel": "blog",
        "url": url,
        "data_file": str(out),
        "git_push_rc": push.returncode,
        "git_push_stderr": push.stderr[:200] if push.returncode != 0 else "",
    }


def publish_x_thread(meta: dict, md: str) -> dict:
    """Post a Postiz X thread (single post with value[] array = thread tweets)."""
    if DRY_RUN or not POSTIZ_KEY:
        return {"channel": "x", "url": None, "dry_run_or_no_key": True}
    integration_id = POSTIZ_X_INTEGRATION_EN or "cmm6d7m5703rwpr0yr5vtme3w"  # @aniccaxxx
    title = meta["title"]
    blog_url = f"https://aniccaai.com/blog/{meta['slug']}"
    first_para = md.split("\n\n")[1][:240] if len(md.split("\n\n")) > 1 else title
    thread_contents = [
        f"NEW research blog: {title}\n\n{first_para}\n\nFull post → {blog_url}\n\n🧵👇",
        "Why now: AI systems are taking on more responsibility every day, but accountability frameworks lag. We're testing what 'responsible AI' actually requires — empirically.",
        f"Methodology: Literature review + scored hypothesis generation + experiment design. Outcomes go to public ledger at {blog_url}.",
        "Looking for collaborators: AI alignment researchers, governance experts, ethics scholars. DM us.",
        "This was written end-to-end by an autonomous AI system. The full pipeline (literature → hypothesis → draft → publish) is open-source.",
    ]
    now_iso = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = json.dumps({
        "type": "now",
        "date": now_iso,
        "shortLink": False,
        "tags": [],
        "posts": [{
            "integration": {"id": integration_id},
            "value": [{"content": c, "image": []} for c in thread_contents],
            "settings": {"__type": "x", "who_can_reply_post": "everyone"},
        }],
    }).encode()
    req = urllib.request.Request(
        "https://api.postiz.com/public/v1/posts",
        data=payload,
        headers={"Authorization": POSTIZ_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        # Postiz response is a list of {postId, integration}
        first = d[0] if isinstance(d, list) and d else {}
        post_id = first.get("postId") if isinstance(first, dict) else None
        return {
            "channel": "x",
            "tweets": [{"ok": True, "post_id": post_id, "url": f"https://x.com/aniccaxxx/status/{post_id}" if post_id else None}],
            "n_tweets": len(thread_contents),
            "blog_url": blog_url,
            "raw": d,
        }
    except Exception as e:
        return {"channel": "x", "tweets": [{"ok": False, "error": str(e)[:300]}], "blog_url": blog_url}


def queue_for_note(meta: dict, md: str) -> dict:
    """Queue for note.com via auto-article-poster (separate skill).
    For now, just write a queue file the auto-article-poster cron picks up.
    """
    queue = WORKSPACE / "note-queue"
    queue.mkdir(parents=True, exist_ok=True)
    out = queue / f"{meta['slug']}.json"
    out.write_text(json.dumps({
        "slug": meta["slug"],
        "title": meta["title"],
        "markdown": md,
        "tags": ["AI", "AI-alignment", "research", "Anicca"],
        "queued_at": dt.datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2))
    return {"channel": "note", "queue_file": str(out), "note": "auto-article-poster will pick this up"}


def main(project: dict) -> int:
    pid = project["id"]
    today = dt.date.today().isoformat()
    md_path = WORKSPACE / "papers" / pid / f"{today}.md"
    meta_path = WORKSPACE / "papers" / pid / f"{today}.meta.json"

    if not (md_path.exists() and meta_path.exists()):
        print(f"publish-3channel[{pid}]: missing draft (md={md_path.exists()}, meta={meta_path.exists()}) — skip")
        return 0

    md = md_path.read_text()
    meta = json.loads(meta_path.read_text())

    # Per Dais 2026-05-08: ONLY blog + X thread. Skip note.com / Substack / X Article.
    results = {}
    results["blog"] = publish_blog(meta, md)
    results["x"] = publish_x_thread(meta, md)

    out_dir = WORKSPACE / "published"
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {"project": pid, "slug": meta["slug"], "date": today, "results": results}
    record_path = out_dir / f"{today}-{meta['slug']}.json"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    blog_url = results["blog"].get("url", "(no url)")
    n_tweets = len(results["x"].get("tweets", []))
    n_ok = sum(1 for t in results["x"].get("tweets", []) if t.get("ok"))
    slack_post(
        f":memo: *auto-research published [{pid}]* — {meta['title']}\n"
        f"• Blog: {blog_url}\n"
        f"• X thread (@aniccaen): {n_ok}/{n_tweets} tweets posted\n"
        f"• Word count: {meta['word_count_approx']} | Citations: {meta['n_papers_cited']}\n"
        f"`{record_path}`"
    )
    print(f"publish-3channel[{pid}]: blog={blog_url}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: publish-3channel.py <project-json>", file=sys.stderr)
        raise SystemExit(64)
    blob = json.loads(sys.argv[1])
    raise SystemExit(main(blob["project"]))
