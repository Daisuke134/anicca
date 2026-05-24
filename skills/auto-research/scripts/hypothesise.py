#!/usr/bin/env python3
"""hypothesise.py — Sakana-style BFTS hypothesis generation.

Reads today's literature pull, calls OpenAI / Anthropic directly with the
K-Dense hypothesis-generation prompt template, generates a tree of
candidate hypotheses, scores each on (novelty, tractability, expected
information gain), writes top-K to hypotheses/<project>/<date>.json.

No dependency on AutoResearchClaw chassis internals — uses the public
LLM APIs and the locally-installed K-Dense `hypothesis-generation` skill
prompt as the system message.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/auto-research"))
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
TOP_K = 5
KDENSE_HYP_SKILL = Path.home() / ".openclaw" / "skills" / "hypothesis-generation" / "SKILL.md"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def call_llm(system: str, user: str) -> str:
    if ANTHROPIC_KEY:
        return _call_anthropic(system, user)
    if not OPENAI_KEY:
        raise RuntimeError("Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY set")
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    return d["choices"][0]["message"]["content"]


def _call_anthropic(system: str, user: str) -> str:
    payload = json.dumps({
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 4000,
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
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    return d["content"][0]["text"]


def load_kdense_prompt() -> str:
    if KDENSE_HYP_SKILL.exists():
        return KDENSE_HYP_SKILL.read_text()
    return (
        "You are an autonomous AI scientist generating research hypotheses. "
        "For each hypothesis, score (novelty 0-1, tractability 0-1, info-gain 0-1) "
        "and provide one-line rationale. Output strict JSON only: "
        '{"hypotheses": [{"text": str, "novelty": float, "tractability": float, '
        '"info_gain": float, "score": float, "rationale": str}, ...]}'
    )


def parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        else:
            cleaned = cleaned.strip()
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {"raw": text, "parse_error": True}


def hypothesise_for_project(project_id: str, lit: dict) -> dict:
    title = lit.get("project") or project_id
    papers = lit.get("results", [])
    paper_summaries = "\n".join(
        f"- {p.get('title','')[:120]} ({p.get('year','?')})"
        for p in papers[:15]
    )
    system = load_kdense_prompt()
    user = (
        f"Research project: {title}\n\n"
        f"Recent literature ({len(papers)} papers):\n{paper_summaries}\n\n"
        f"Generate {TOP_K} candidate hypotheses. Score each on novelty, "
        f"tractability, info_gain (each 0-1). Compute score = "
        f"0.4*novelty + 0.3*tractability + 0.3*info_gain. "
        f"Each hypothesis must be tractable in <30 days of compute. "
        f"Output strict JSON only."
    )
    response = call_llm(system, user)
    return parse_json_response(response)


def main(project: dict) -> int:
    pid = project["id"]
    today = dt.date.today().isoformat()
    lit_path = WORKSPACE / "literature" / pid / f"{today}.json"
    out_dir = WORKSPACE / "hypotheses" / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today}.json"

    if not lit_path.exists():
        print(f"hypothesise[{pid}]: no literature for today at {lit_path} — skipping.")
        return 0

    lit = json.loads(lit_path.read_text())

    if DRY_RUN:
        plan = {"project": pid, "stub": True, "would_query_lit_count": len(lit.get("results", []))}
        out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        print(f"hypothesise[{pid}][DRY_RUN]: wrote stub {out_path}")
        return 0

    try:
        hypotheses = hypothesise_for_project(pid, lit)
    except Exception as e:
        err = {"project": pid, "error": str(e)[:500]}
        out_path.write_text(json.dumps(err, indent=2, ensure_ascii=False))
        print(f"hypothesise[{pid}]: ERROR {e}", file=sys.stderr)
        return 1

    out_path.write_text(json.dumps({
        "project": pid,
        "scraped_at": today,
        "hypotheses": hypotheses,
    }, ensure_ascii=False, indent=2))
    print(f"hypothesise[{pid}]: wrote {out_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: hypothesise.py <project-json>", file=sys.stderr)
        raise SystemExit(64)
    blob = json.loads(sys.argv[1])
    raise SystemExit(main(blob["project"]))
