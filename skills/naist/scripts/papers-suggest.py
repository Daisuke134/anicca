#!/usr/bin/env python3
"""papers-suggest.py — daily 08:00 JST.

Reads ~/.openclaw/state/naist/<slug>/research-profile.json (keywords) and queries
arXiv for the 5 most-recent matching papers. For each paper, posts a Slack card
to the slug's metrics channel with title / authors / abstract / arXiv URL plus
a "how to use" hint generated from the abstract + research-profile.

Output: Slack post (channel from ~/.openclaw/state/naist/<slug>/slack_channel.txt).
Workspace artifact: ~/.openclaw/workspace/naist/papers-<ymd>-<slug>.json
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/naist"))
STATE_ROOT = Path(os.path.expanduser("~/.openclaw/state/naist"))
SLUG = os.environ.get("SLUG", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
ARXIV_BASE = "http://export.arxiv.org/api/query"
ARXIV_TIMEOUT = int(os.environ.get("ARXIV_TIMEOUT", "20"))
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def load_research_profile(slug: str) -> dict:
    p = STATE_ROOT / slug / "research-profile.json"
    if not p.exists():
        return {"research_keywords": []}
    return json.loads(p.read_text())


def slack_channel_for(slug: str) -> str | None:
    p = STATE_ROOT / slug / "slack_channel.txt"
    return p.read_text().strip() if p.exists() else None


def query_arxiv(keywords: list[str], max_results: int = 5) -> list[dict]:
    if not keywords:
        return []
    # OR-join keywords; sort by submittedDate desc
    q = " OR ".join(f'all:"{kw}"' for kw in keywords)
    params = {
        "search_query": q,
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "anicca-naist/1.0"})
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=ARXIV_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code != 429 or attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
        except TimeoutError as e:
            last_err = e
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    else:
        raise last_err

    root = ET.fromstring(body)
    papers = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " ")
        title = re.sub(r"\s+", " ", title)
        summary = (entry.findtext(f"{ATOM_NS}summary") or "").strip().replace("\n", " ")
        summary = re.sub(r"\s+", " ", summary)
        link = ""
        for ln in entry.findall(f"{ATOM_NS}link"):
            if ln.get("rel") == "alternate":
                link = ln.get("href") or ""
                break
        published = entry.findtext(f"{ATOM_NS}published") or ""
        authors = [
            (a.findtext(f"{ATOM_NS}name") or "").strip()
            for a in entry.findall(f"{ATOM_NS}author")
        ]
        papers.append({
            "title": title,
            "authors": authors,
            "abstract": summary[:600],
            "url": link,
            "published": published,
        })
    return papers


def utility_hint(paper: dict, profile: dict) -> str:
    """Lightweight rule-based hint. Agent can refine later via prompt."""
    abstract = paper["abstract"].lower()
    keywords = [k.lower() for k in profile.get("research_keywords", [])]
    matched = [k for k in keywords if k in abstract]
    if not matched:
        return "Topic adjacent — review for tangential connection."
    if "benchmark" in abstract:
        return f"Possible benchmark/eval source for: {', '.join(matched)}."
    if "dataset" in abstract:
        return f"Dataset candidate for: {', '.join(matched)}."
    if "method" in abstract or "framework" in abstract:
        return f"Method/framework reference for: {', '.join(matched)}."
    return f"Background reading for: {', '.join(matched)}."


def slack_post(channel: str, text: str, dry_run: bool = False) -> dict:
    if dry_run or not SLACK_TOKEN:
        print(f"[DRY] would post to {channel}: {text[:200]}...")
        return {"ok": False, "dry_run": True}
    import urllib.request as ur
    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = ur.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json; charset=utf-8"},
    )
    with ur.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    if not SLUG:
        print("papers-suggest: SLUG env required", file=sys.stderr)
        return 64

    profile = load_research_profile(SLUG)
    keywords = profile.get("research_keywords", [])
    if not keywords:
        print(f"papers-suggest[{SLUG}]: research-profile.json missing 'research_keywords' — skip")
        return 0

    print(f"papers-suggest[{SLUG}]: querying arXiv for {len(keywords)} keywords")
    papers = query_arxiv(keywords, max_results=5)
    print(f"papers-suggest[{SLUG}]: arXiv returned {len(papers)} papers")

    today = dt.date.today().isoformat()
    out = WORKSPACE / f"papers-{today}-{SLUG}.json"
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    enriched = [{**p, "utility_hint": utility_hint(p, profile)} for p in papers]
    out.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
    print(f"papers-suggest[{SLUG}]: wrote {out}")

    if not papers:
        return 0

    channel = slack_channel_for(SLUG)
    if not channel:
        print(f"papers-suggest[{SLUG}]: no slack_channel.txt — skipping post")
        return 0

    lines = [
        f":books: *{{profile.education.institution}} 関連論文 daily ({SLUG})* — {len(papers)} 件 (キーワード: {', '.join(keywords)[:120]})",
    ]
    for p in enriched:
        first_author = p["authors"][0] if p["authors"] else "?"
        more = f" + {len(p['authors'])-1}" if len(p["authors"]) > 1 else ""
        lines.append(
            f"\n*{p['title'][:160]}*\n"
            f"_{first_author}{more} · {p['published'][:10]}_\n"
            f"<{p['url']}|arXiv>\n"
            f"> {p['utility_hint']}"
        )
    msg = "\n".join(lines)

    res = slack_post(channel, msg, dry_run=DRY_RUN)
    print(f"papers-suggest[{SLUG}]: slack_post → ok={res.get('ok')} ts={res.get('ts')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
