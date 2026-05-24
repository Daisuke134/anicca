#!/usr/bin/env python3
"""draft-paper.py — write a research blog post draft from literature + hypothesis.

Combines today's literature + hypotheses into a 1500-2500-word long-form
markdown for blog/Substack/X publish (NOT arXiv preprint per v2.4 spec).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/auto-research"))
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def call_llm(system: str, user: str, max_tokens: int = 6000) -> str:
    if ANTHROPIC_KEY:
        payload = json.dumps({
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.loads(r.read().decode())
        return d["content"][0]["text"]
    if not OPENAI_KEY:
        raise RuntimeError("Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY set")
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.6,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode())
    return d["choices"][0]["message"]["content"]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", text.lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def main(project: dict) -> int:
    pid = project["id"]
    title = project.get("title", pid)
    today = dt.date.today().isoformat()
    lit_path = WORKSPACE / "literature" / pid / f"{today}.json"
    hyp_path = WORKSPACE / "hypotheses" / pid / f"{today}.json"
    out_dir = WORKSPACE / "papers" / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today}.md"
    meta_path = out_dir / f"{today}.meta.json"

    if not lit_path.exists() or not hyp_path.exists():
        print(f"draft-paper[{pid}]: missing inputs — skip")
        return 0
    lit = json.loads(lit_path.read_text())
    hyp = json.loads(hyp_path.read_text())

    if DRY_RUN:
        out_path.write_text(f"# Draft for {title} (DRY_RUN stub)\n")
        meta_path.write_text(json.dumps({"project": pid, "stub": True}))
        return 0

    papers = lit.get("results", [])[:10]
    hypotheses = hyp.get("hypotheses", {})
    if isinstance(hypotheses, dict):
        hypotheses = hypotheses.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        hypotheses = []

    paper_summaries = "\n".join(
        f"- {p.get('title','')[:140]} ({p.get('year','?')}, {p.get('source','?')})"
        for p in papers
    )
    hyp_text = "\n".join(
        f"- {h.get('hypothesis', h.get('text', ''))[:200]} (score: {h.get('score', '?')})"
        for h in hypotheses[:5]
    )

    system = (
        "You are an autonomous AI scientist writing a research blog post / preprint draft. "
        "Topic theme: AI alignment, AI responsibility, AI trust building, AI entity GDP, "
        "mindfulness, autonomous agents. "
        "Style: Substack-friendly long-form (1500-2500 words). "
        "Structure: Problem → Why now → Related work → Hypothesis → Experiment design → "
        "Discussion → Open questions → Call for collaboration. "
        "Every claim cites a real paper from the supplied list (inline [Author Year]). "
        "Output PURE MARKDOWN, no preamble, no code fences."
    )
    user = (
        f"# {title}\n\n"
        f"## Top hypotheses (scored)\n{hyp_text}\n\n"
        f"## Recent literature\n{paper_summaries}\n\n"
        f"Pick the highest-scored hypothesis as the central claim. "
        f"Use the literature for related-work + citations. "
        f"Discussion explicitly links to AI Responsibility / AI Alignment / AI Trust building implications. "
        f"End with Call for Collaboration paragraph (we are Anicca, building autonomous "
        f"AI agents — looking for co-authors / reviewers / collaborators)."
    )

    md = call_llm(system, user)
    out_path.write_text(md)
    meta = {
        "project": pid,
        "title": title,
        "date": today,
        "slug": slugify(f"{pid}-{today}"),
        "n_papers_cited": len(papers),
        "n_hypotheses_considered": len(hypotheses),
        "word_count_approx": len(md.split()),
        "paper_md_path": str(out_path),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"draft-paper[{pid}]: wrote {out_path} ({meta['word_count_approx']} words)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: draft-paper.py <project-json>", file=sys.stderr)
        raise SystemExit(64)
    blob = json.loads(sys.argv[1])
    raise SystemExit(main(blob["project"]))
