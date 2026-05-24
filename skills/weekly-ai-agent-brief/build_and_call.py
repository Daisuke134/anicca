#!/usr/bin/env python3
"""Build Grok synthesis prompt from 7-day workspace JSONs, call Grok, split response into brief.md + slides.md."""
from __future__ import annotations
import argparse
import datetime
import json
import os
import sys
import urllib.request


def collect_recent(dir_path: str, prefix: str, days: int = 7) -> str:
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    chunks = []
    for i in range(days):
        d = today - datetime.timedelta(days=i)
        f = os.path.join(dir_path, f"{prefix}{d.isoformat()}.json")
        if os.path.isfile(f):
            with open(f, "r", encoding="utf-8") as fh:
                chunks.append(f"\n═════════════════════ {prefix}{d.isoformat()}.json ═════════════════════\n{fh.read()}")
    return "".join(chunks)


def build_prompt(date_jst: str, papers: str, digest: str, mufg: str) -> str:
    return f"""You are Dais's weekly AI agent intelligence brief writer. Dais is:
- MUIT (MUFG IT) data science department, EPOC project (Salesforce Financial Services Cloud + Tableau, scaling to 26,000 employees in FY2026)
- ICLR 2026 Sao Paulo presenter
- World-class AI agent / AI safety expert
- Building Anicca (proactive behavioral-change AI agent)

Below are the past 7 days of raw data from 3 sources:
1. latest-papers — AI agent / LLM / autonomous agent papers from X
2. dais-x-feed-digest — 5 themes (model launches / AI entities / AI money / mobile app growth / Claude Code)
3. mufg-epoc-watcher — 5 themes (Salesforce Agentforce / banking AI deployment / AI safety regulation / Anthropic enterprise / AI agent CRM)

Synthesize into TWO markdown documents in Japanese, separated by exactly the line "===SLIDES_BELOW===".

Document 1 (above the separator) — A4 1-page brief:

# Weekly AI Agent Brief — Week of {date_jst}

## 🎯 Top 3 takeaways
1. (1 行)
2. (1 行)
3. (1 行)

## 📚 Key papers (3-5)
| Title | Authors | Why it matters | Anicca/EPOC application |
|-------|---------|----------------|-------------------------|
| ... | ... | ... | ... |

## 🚀 Product / agent launches (3-5)
- (各 1 行)

## 🛡️ Safety & alignment (2-3)
- (各 1 行)

## 🏦 Banking / financial AI (2-3)
- (各 1 行)

## 🎤 Use this week
- ICLR Sao Paulo: 追加すべき slide 1 件
- MUIT 勉強会: 1 行 talking point
- Anicca: 1 個 implementation idea

## 🔮 Next-week prediction (3 行)
- ...

Document 2 (below the separator) — Marp slides outline, 8-10 slides total:

---
marp: true
theme: default
paginate: true
---

# Weekly AI Agent Brief
## Week of {date_jst}

By Dais (MUIT data science / ICLR 2026 Sao Paulo presenter)

---

(slide 2: top 3 takeaways)
(slide 3-5: key papers, 1 per slide)
(slide 6-7: launches)
(slide 8: safety)
(slide 9: banking AI)
(slide 10: 来週何が来るか)

Each slide: title + 3-5 bullet points + 1 source citation if relevant.

=== Source data (last 7 days) ===

--- latest-papers ---
{papers}

--- dais-x-feed-digest ---
{digest}

--- mufg-epoc-watcher ---
{mufg}

=== End of source data ===

Now write the two documents in Japanese. No preamble. Start directly with "# Weekly AI Agent Brief".
"""


def call_grok(api_key: str, prompt: str) -> dict:
    body = json.dumps({"model": "grok-4-fast", "input": prompt}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.x.ai/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_text(resp: dict) -> str:
    parts = []
    for item in resp.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for c in item.get("content", []) or []:
            if c.get("type") == "output_text":
                parts.append(c.get("text", ""))
    return "".join(parts)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--xai-key", required=True)
    p.add_argument("--brief-out", required=True)
    p.add_argument("--slides-out", required=True)
    p.add_argument("--raw-out", required=True)
    p.add_argument("--resp-out", required=True)
    args = p.parse_args()

    home = os.path.expanduser("~")
    papers = collect_recent(os.path.join(home, ".openclaw/workspace/latest-papers"), "papers_")
    digest = collect_recent(os.path.join(home, ".openclaw/workspace/dais-x-feed-digest"), "digest_")
    mufg = collect_recent(os.path.join(home, ".openclaw/workspace/mufg-epoc-watcher"), "brief_")

    print(f"[build_and_call.py] input bytes — papers={len(papers)} digest={len(digest)} mufg={len(mufg)}", file=sys.stderr)

    with open(args.raw_out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": args.date,
                "papersBytes": len(papers),
                "digestBytes": len(digest),
                "mufgBytes": len(mufg),
            },
            f,
            indent=2,
        )

    prompt = build_prompt(args.date, papers, digest, mufg)

    try:
        resp = call_grok(args.xai_key, prompt)
    except Exception as e:
        print(f"[build_and_call.py] Grok call failed: {e}", file=sys.stderr)
        with open(args.resp_out, "w", encoding="utf-8") as f:
            json.dump({"error": str(e)}, f)
        return 2

    with open(args.resp_out, "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)

    text = extract_text(resp)
    if not text:
        print("[build_and_call.py] ERROR: empty Grok output", file=sys.stderr)
        return 3

    sep = "===SLIDES_BELOW==="
    if sep in text:
        brief_part, slides_part = text.split(sep, 1)
    else:
        brief_part = text
        slides_part = "(slides outline missing — separator not found in Grok output)"

    with open(args.brief_out, "w", encoding="utf-8") as f:
        f.write(brief_part.strip() + "\n")
    with open(args.slides_out, "w", encoding="utf-8") as f:
        f.write(slides_part.strip() + "\n")

    print(f"[build_and_call.py] done. brief={args.brief_out} slides={args.slides_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
