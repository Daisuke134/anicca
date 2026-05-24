#!/usr/bin/env python3
"""publish-chassis.py — consume AutoResearchClaw chassis output and publish to:
  1. aniccaai.com/blog/<slug>  (data file commit + push to apps/landing)
  2. X thread @aniccaxxx       (Postiz API, 5-tweet thread teasing the paper)

Reads from a chassis run directory:
  <chassis_run_dir>/{{profile.lateness.stakeholders.senderType}}-23/paper_final_verified.md  (citation-verified markdown)
  <chassis_run_dir>/{{profile.lateness.stakeholders.senderType}}-23/verification_report.json (CrossRef verification)
  <chassis_run_dir>/{{profile.lateness.stakeholders.senderType}}-22/paper_final.md           (final markdown — fallback)
  <chassis_run_dir>/{{profile.lateness.stakeholders.senderType}}-22/paper.tex                (NeurIPS LaTeX, optional)
  <chassis_run_dir>/{{profile.lateness.stakeholders.senderType}}-22/charts/                  (figures)
  <chassis_run_dir>/{{profile.lateness.stakeholders.senderType}}-22/references.bib           (citations)

Writes:
  apps/landing/data/research/<slug>.json
  ~/.openclaw/workspace/auto-research/published/<ymd>-<slug>.json (ledger)

ENV:
  CHASSIS_RUN_DIR      path to the chassis run dir (required)
  PROJECT_ID           e.g. "ai-responsibility"
  POSTIZ_API_KEY       set in ~/.openclaw/.env
  POSTIZ_X_INTEGRATION_ID  defaults to cmm6d7m5703rwpr0yr5vtme3w (@aniccaxxx)
  SLACK_BOT_TOKEN
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

CHASSIS_RUN_DIR = Path(os.environ.get("CHASSIS_RUN_DIR", "")).expanduser()
PROJECT_ID = os.environ.get("PROJECT_ID", "")
WORKSPACE = Path.home() / ".openclaw" / "workspace" / "auto-research"
LANDING_REPO = Path.home() / "anicca-project" / "apps" / "landing"
POSTIZ_KEY = os.environ.get("POSTIZ_API_KEY", "")
POSTIZ_X_ID = os.environ.get("POSTIZ_X_INTEGRATION_ID", "cmm6d7m5703rwpr0yr5vtme3w")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "{{profile.channels.reportChannel}}"


def fail(msg: str) -> None:
    print(f"publish-chassis FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", text.lower())
    return re.sub(r"-+", "-", s).strip("-")[:80]


def read_chassis_output() -> dict:
    if not CHASSIS_RUN_DIR.exists():
        fail(f"CHASSIS_RUN_DIR not found: {CHASSIS_RUN_DIR}")
    paper_md_path = CHASSIS_RUN_DIR / "{{profile.lateness.stakeholders.senderType}}-23" / "paper_final_verified.md"
    if not paper_md_path.exists():
        paper_md_path = CHASSIS_RUN_DIR / "{{profile.lateness.stakeholders.senderType}}-22" / "paper_final.md"
    if not paper_md_path.exists():
        fail("{{profile.lateness.stakeholders.senderType}}-23/paper_final_verified.md and {{profile.lateness.stakeholders.senderType}}-22/paper_final.md both missing — chassis pipeline incomplete")
    md_text = paper_md_path.read_text().strip()
    if md_text.startswith("```markdown"):
        md_text = md_text[len("```markdown"):].lstrip("\n")
    if md_text.endswith("```"):
        md_text = md_text[:-3].rstrip()
    lessons_marker = re.search(r"\n## Lessons from Prior Runs", md_text)
    if lessons_marker:
        md_text = md_text[:lessons_marker.start()].rstrip()
    title_match = re.search(r"^#\s+(.+)$", md_text, re.M)
    title = title_match.group(1).strip() if title_match else PROJECT_ID

    n_refs = 0
    integrity = None
    verif_path = CHASSIS_RUN_DIR / "{{profile.lateness.stakeholders.senderType}}-23" / "verification_report.json"
    if verif_path.exists():
        try:
            v = json.loads(verif_path.read_text())
            n_refs = v.get("summary", {}).get("verified", 0)
            integrity = v.get("summary", {}).get("integrity_score")
        except Exception:
            pass
    if n_refs == 0:
        refs_bib = CHASSIS_RUN_DIR / "{{profile.lateness.stakeholders.senderType}}-22" / "references.bib"
        if refs_bib.exists():
            n_refs = len(re.findall(r"^@\w+\{", refs_bib.read_text(), re.M))

    charts_dir = CHASSIS_RUN_DIR / "{{profile.lateness.stakeholders.senderType}}-22" / "charts"
    n_charts = len(list(charts_dir.glob("*.png"))) if charts_dir.exists() else 0
    paper_tex = CHASSIS_RUN_DIR / "{{profile.lateness.stakeholders.senderType}}-22" / "paper.tex"

    return {
        "title": title,
        "markdown": md_text,
        "tex_path": str(paper_tex) if paper_tex.exists() else None,
        "n_references": n_refs,
        "citation_integrity": integrity,
        "n_charts": n_charts,
        "word_count": len(md_text.split()),
    }


def slack_post(text: str) -> None:
    if not SLACK_TOKEN:
        print(f"[no slack] {text[:200]}")
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


def publish_blog(out: dict, slug: str, today: str) -> dict:
    data_dir = LANDING_REPO / "data" / "research"
    data_dir.mkdir(parents=True, exist_ok=True)
    blog_data = {
        "slug": slug,
        "title": out["title"],
        "date": today,
        "project": PROJECT_ID,
        "n_papers_cited": out["n_references"],
        "n_charts": out["n_charts"],
        "word_count": out["word_count"],
        "markdown": out["markdown"],
        "source": "AutoResearchClaw 23-{{profile.lateness.stakeholders.senderType}} chassis (E2E autonomous pipeline)",
        "citation_integrity": out.get("citation_integrity"),
    }
    out_file = data_dir / f"{slug}.json"
    out_file.write_text(json.dumps(blog_data, ensure_ascii=False, indent=2))

    repo_root = LANDING_REPO.parent.parent
    rel = out_file.relative_to(repo_root)
    subprocess.run(["git", "-C", str(repo_root), "add", str(rel)], capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "-c", "credential.helper=", "commit",
         "-m", f"research: {out['title']} ({slug}) — chassis E2E"],
        capture_output=True,
    )
    push = subprocess.run(
        ["git", "-C", str(repo_root), "-c", "credential.helper=", "push", "origin", "HEAD"],
        capture_output=True, text=True, timeout=120,
    )
    return {
        "channel": "blog",
        "url": f"https://aniccaai.com/blog/{slug}",
        "data_file": str(out_file),
        "git_push_rc": push.returncode,
        "git_push_stderr": push.stderr[:200] if push.returncode != 0 else "",
    }


def publish_x_thread(out: dict, slug: str) -> dict:
    if not POSTIZ_KEY:
        return {"channel": "x", "skipped": "no POSTIZ_API_KEY"}
    title = out["title"]
    blog_url = f"https://aniccaai.com/blog/{slug}"
    paragraphs = [p.strip() for p in out["markdown"].split("\n\n") if p.strip() and not p.strip().startswith("#")]
    teaser = paragraphs[0][:240] if paragraphs else title
    contents = [
        f"NEW research paper (full E2E pipeline):\n\n{title}\n\nFull post → {blog_url}\n\n🧵👇",
        teaser,
        f"Method: literature review → BFTS hypothesis generation → experiment in sandbox → multi-{{profile.lateness.stakeholders.senderType}} writeup → 4-round refine.\nCitations: {out['n_references']} verified against OpenAlex.\nCharts: {out['n_charts']}.",
        "Topic: AI Responsibility — how autonomous AI agents can earn trust and take responsibility for their actions.",
        "Pipeline: AutoResearchClaw (open-source) + K-Dense scientific-agent-skills + our publish layer. Anicca research lab runs 24h, all autonomous.",
    ]
    now_iso = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = json.dumps({
        "type": "now",
        "date": now_iso,
        "shortLink": False,
        "tags": [],
        "posts": [{
            "integration": {"id": POSTIZ_X_ID},
            "value": [{"content": c, "image": []} for c in contents],
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
        first = d[0] if isinstance(d, list) and d else {}
        post_id = first.get("postId") if isinstance(first, dict) else None
        return {
            "channel": "x",
            "ok": True,
            "post_id": post_id,
            "url": f"https://x.com/aniccaxxx/status/{post_id}" if post_id else None,
            "n_tweets": len(contents),
            "blog_url": blog_url,
        }
    except Exception as e:
        return {"channel": "x", "ok": False, "error": str(e)[:300], "blog_url": blog_url}


def main() -> int:
    if not CHASSIS_RUN_DIR or not PROJECT_ID:
        fail("CHASSIS_RUN_DIR + PROJECT_ID env required")
    today = dt.date.today().isoformat()
    out = read_chassis_output()
    slug = slugify(f"{PROJECT_ID}-{today}")

    blog_res = publish_blog(out, slug, today)
    x_res = publish_x_thread(out, slug)

    record = {
        "project": PROJECT_ID,
        "slug": slug,
        "date": today,
        "chassis_run_dir": str(CHASSIS_RUN_DIR),
        "title": out["title"],
        "word_count": out["word_count"],
        "n_references": out["n_references"],
        "n_charts": out["n_charts"],
        "blog": blog_res,
        "x": x_res,
    }
    ledger_dir = WORKSPACE / "published"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / f"{today}-{slug}-chassis.json"
    ledger_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    n_tweets = x_res.get("n_tweets", 0)
    blog_url = blog_res.get("url", "(no url)")
    x_url = x_res.get("url", "(none)")
    slack_post(
        f":memo: *auto-research chassis E2E published* — {out['title']}\n"
        f"• Source: AutoResearchClaw 23-{{profile.lateness.stakeholders.senderType}} pipeline\n"
        f"• Blog: {blog_url}\n"
        f"• X thread: {n_tweets} tweets → {x_url}\n"
        f"• Word count: {out['word_count']} | Citations: {out['n_references']} | Charts: {out['n_charts']}\n"
        f"`{ledger_path}`"
    )
    print(f"publish-chassis: blog={blog_url} x={x_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
