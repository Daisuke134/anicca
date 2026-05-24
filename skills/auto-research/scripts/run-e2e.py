#!/usr/bin/env python3
"""run-e2e.py — single-shot end-to-end research pipeline (no chassis dep).

For one project, executes:
  Stage 1: literature-pull  (arXiv + Semantic Scholar APIs, real)
  Stage 2: hypothesise      (OpenAI: 3 testable hypotheses from literature)
  Stage 3: draft-paper      (OpenAI: literature review markdown, ~1500 words)
  Stage 4: publish          (Slack post with summary + write artifacts to disk)

Inputs:
  PROJECT_ID env var (e.g. "ai-mindfulness") — picks project from projects.yaml
  (or PROJECT_ID="auto" to use round-robin cursor — default = ai-mindfulness)
  AUTO_RESEARCH_DRY_RUN=true → no API calls, prints plan

Outputs (workspace/auto-research/<pid>/<date>/):
  literature.json   (arXiv + S2 results)
  hypothesis.json   (3 testable hypotheses + reasoning)
  draft.md          (1500-word literature review markdown)
  summary.json      (run metadata)

Env required:
  OPENAI_API_KEY
  SLACK_BOT_TOKEN (optional — skipped if missing)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "auto-research"
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "auto-research"
PROJECTS_YAML = SKILL_DIR / "projects.yaml"
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
XAI_KEY = os.environ.get("XAI_API_KEY", "")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL_ID", "")
TODAY = dt.date.today().isoformat()


def log({{profile.lateness.stakeholders.senderType}}: str, msg: str) -> None:
    print(f"[run-e2e:{{{profile.lateness.stakeholders.senderType}}}] {msg}")


# ─── projects.yaml minimal loader ───────────────────────────────────────────
def load_projects() -> list[dict]:
    try:
        import yaml  # type: ignore
        with open(PROJECTS_YAML) as f:
            return yaml.safe_load(f)["projects"]
    except ImportError:
        pass
    # Minimal fallback parser
    text = PROJECTS_YAML.read_text()
    projects: list[dict] = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#") or line.strip() == "projects:":
            continue
        if line.startswith("  - id:"):
            if cur:
                projects.append(cur)
            cur = {"id": line.split(":", 1)[1].strip()}
        elif cur is not None and line.startswith("    "):
            k, _, v = line.strip().partition(":")
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
            else:
                v = v.strip().strip('"')
            cur[k.strip()] = v
    if cur:
        projects.append(cur)
    return projects


def pick_project() -> dict:
    pid_env = os.environ.get("PROJECT_ID", "ai-mindfulness")
    projects = load_projects()
    if pid_env == "auto":
        cursor_path = WORKSPACE / ".cursor.json"
        try:
            cur = json.loads(cursor_path.read_text())
        except Exception:
            cur = {"next_index": 0}
        idx = cur.get("next_index", 0) % len(projects)
        return projects[idx]
    for p in projects:
        if p["id"] == pid_env:
            return p
    raise SystemExit(f"project_id {pid_env!r} not found in projects.yaml")


# ─── Stage 1: literature-pull (arXiv + Semantic Scholar) ────────────────────
def arxiv_search(query: str, categories: list[str], limit: int = 15) -> list[dict]:
    cat_filter = ""
    if categories:
        cat_clauses = " OR ".join(f"cat:{c}" for c in categories)
        cat_filter = f" AND ({cat_clauses})"
    q = f"all:{query}{cat_filter}"
    url = (
        "https://export.arxiv.org/api/query?"
        + urllib.parse.urlencode(
            {
                "search_query": q,
                "start": 0,
                "max_results": limit,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )
    )
    req = urllib.request.Request(url, headers={"User-Agent": "anicca-auto-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")
    # Parse entries with regex (avoid xml.etree namespace pain for short script)
    results = []
    for m in re.finditer(r"<entry>(.+?)</entry>", xml, re.S):
        e = m.group(1)
        title = re.search(r"<title>(.+?)</title>", e, re.S)
        abstract = re.search(r"<summary>(.+?)</summary>", e, re.S)
        published = re.search(r"<published>(.+?)</published>", e)
        arxiv_id = re.search(r"<id>http://arxiv\.org/abs/([^<]+)</id>", e)
        authors = [a.group(1).strip() for a in re.finditer(r"<author>\s*<name>(.+?)</name>", e, re.S)]
        results.append(
            {
                "title": title.group(1).strip().replace("\n", " ") if title else None,
                "abstract": abstract.group(1).strip().replace("\n", " ") if abstract else None,
                "published": published.group(1) if published else None,
                "arxiv_id": arxiv_id.group(1).strip() if arxiv_id else None,
                "authors": authors,
                "source": "arxiv",
            }
        )
    return results


def semantic_scholar_search(query: str, limit: int = 10) -> list[dict]:
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search?"
        + urllib.parse.urlencode(
            {
                "query": query,
                "limit": limit,
                "fields": "title,abstract,year,authors,externalIds,citationCount",
            }
        )
    )
    req = urllib.request.Request(url, headers={"User-Agent": "anicca-auto-research/1.0"})
    # Polite pre-call sleep + retry on 429 (S2 rate-limits aggressively)
    time.sleep(1)
    data = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as he:
            if he.code == 429 and attempt < 2:
                retry_after = int(he.headers.get("Retry-After", "5"))
                log("literature", f"S2 429 — sleeping {retry_after}s (attempt {attempt + 1}/3)")
                time.sleep(retry_after)
                continue
            log("literature", f"S2 HTTPError {he.code}: {he}")
            return []
        except Exception as e:
            log("literature", f"S2 fetch failed: {e}")
            return []
    if data is None:
        return []
    results = []
    for p in data.get("data", []):
        results.append(
            {
                "title": p.get("title"),
                "abstract": p.get("abstract"),
                "year": p.get("year"),
                "authors": [a.get("name") for a in (p.get("authors") or [])],
                "doi": (p.get("externalIds") or {}).get("DOI"),
                "citations": p.get("citationCount"),
                "source": "semantic_scholar",
            }
        )
    return results


def {{profile.lateness.stakeholders.senderType}}_literature(project: dict, out_dir: Path) -> dict:
    log("literature", f"searching for: {project['title']}")
    title = project["title"]
    cats = project.get("arxiv_categories") or []
    if DRY_RUN:
        out = {"project": project["id"], "dry_run": True, "queries": [title]}
        (out_dir / "literature.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        log("literature", "DRY — wrote stub")
        return out

    arxiv_papers = arxiv_search(title, cats, limit=15)
    log("literature", f"arXiv → {len(arxiv_papers)} papers")
    time.sleep(2)  # polite rate
    s2_papers = semantic_scholar_search(title, limit=10)
    log("literature", f"S2 → {len(s2_papers)} papers")

    out = {
        "project": project["id"],
        "title": project["title"],
        "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
        "arxiv": arxiv_papers,
        "semantic_scholar": s2_papers,
        "total": len(arxiv_papers) + len(s2_papers),
    }
    (out_dir / "literature.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    log("literature", f"wrote literature.json ({out['total']} papers)")
    return out


# ─── LLM chat helper (provider-agnostic with fallback) ─────────────────────
def gemini_chat(prompt: str, model: str = "gemini-2.5-flash", max_tokens: int = 4000) -> str:
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
        }
    ).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    candidates = data.get("candidates") or []
    if not candidates:
        feedback = data.get("promptFeedback") or {}
        raise RuntimeError(f"gemini: no candidates (feedback={feedback})")
    cand = candidates[0]
    content = cand.get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise RuntimeError(f"gemini: no parts (finishReason={cand.get('finishReason')})")
    text = parts[0].get("text")
    if not text:
        raise RuntimeError(f"gemini: empty text (finishReason={cand.get('finishReason')})")
    return text


def openai_chat(messages: list[dict], model: str = "gpt-4o-mini", max_tokens: int = 1500) -> str:
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    body = json.dumps(
        {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"openai: no choices (data={list(data.keys())})")
    return choices[0].get("message", {}).get("content", "")


def llm_chat(prompt: str, max_tokens: int = 4000) -> str:
    """Provider-agnostic chat. Tries Gemini → OpenAI → raise."""
    errors = []
    if GEMINI_KEY:
        try:
            return gemini_chat(prompt, max_tokens=max_tokens)
        except Exception as e:
            errors.append(f"gemini: {e}")
    if OPENAI_KEY:
        try:
            return openai_chat(
                [{"role": "user", "content": prompt}], max_tokens=max_tokens
            )
        except Exception as e:
            errors.append(f"openai: {e}")
    raise RuntimeError(f"all LLM providers failed: {errors}")


# ─── Stage 2: hypothesise ────────────────────────────────────────────────────
def {{profile.lateness.stakeholders.senderType}}_hypothesise(project: dict, lit: dict, out_dir: Path) -> dict:
    log("hypothesise", f"generating hypotheses for {project['id']}")
    if DRY_RUN:
        out = {"project": project["id"], "dry_run": True, "hypotheses": []}
        (out_dir / "hypothesis.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        return out

    # Build context from first ~10 papers
    papers = (lit.get("arxiv") or [])[:8] + (lit.get("semantic_scholar") or [])[:5]
    context_lines = []
    for p in papers:
        title = p.get("title") or "(no title)"
        abstract = (p.get("abstract") or "")[:300]
        context_lines.append(f"- {title}\n  {abstract}")
    context = "\n".join(context_lines)

    prompt = f"""You are conducting autonomous research for the project: "{project['title']}".
Description: {project.get('description', '')}

Recent literature ({len(papers)} papers):
{context}

Generate 3 testable, novel research hypotheses informed by this literature.
Output as JSON with the schema:
{{
  "hypotheses": [
    {{
      "statement": "...",   // ~25 words, falsifiable
      "rationale": "...",   // why this is supported by/contrasts with the literature, ~60 words
      "test_design": "...", // brief outline of how to falsify, ~50 words
      "novelty": "..."      // what's new relative to cited papers, ~40 words
    }}
  ]
}}
Return ONLY the JSON object, no markdown fence."""

    response = llm_chat(prompt, max_tokens=4000)
    # Strip code fences if model added them
    response = re.sub(r"^```(?:json)?\s*", "", response.strip())
    response = re.sub(r"\s*```$", "", response)
    parsed: dict | None = None
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as e:
        # Salvage: try regex to extract complete hypothesis objects
        log("hypothesise", f"JSON parse failed: {e}; attempting salvage")
        salvaged = []
        for hm in re.finditer(
            r'\{\s*"statement"\s*:\s*"([^"]+)"\s*,\s*"rationale"\s*:\s*"([^"]+)"\s*,\s*"test_design"\s*:\s*"([^"]+)"\s*,\s*"novelty"\s*:\s*"([^"]+)"\s*\}',
            response,
            re.S,
        ):
            salvaged.append({
                "statement": hm.group(1).strip(),
                "rationale": hm.group(2).strip(),
                "test_design": hm.group(3).strip(),
                "novelty": hm.group(4).strip(),
            })
        if salvaged:
            parsed = {"hypotheses": salvaged, "salvaged": True}
            log("hypothesise", f"salvaged {len(salvaged)} hypotheses via regex")
        else:
            parsed = {"raw": response, "parse_error": str(e), "hypotheses": []}

    out = {
        "project": project["id"],
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "literature_count": len(papers),
        **parsed,
    }
    (out_dir / "hypothesis.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    n = len(parsed.get("hypotheses", [])) if isinstance(parsed, dict) else 0
    log("hypothesise", f"wrote hypothesis.json ({n} hypotheses)")
    return out


# ─── Stage 3: draft-paper ────────────────────────────────────────────────────
def {{profile.lateness.stakeholders.senderType}}_draft_paper(project: dict, lit: dict, hyp: dict, out_dir: Path) -> str:
    log("draft", f"writing literature review for {project['id']}")
    if DRY_RUN:
        md = f"# {project['title']} (DRY_RUN)\n\nNo content."
        (out_dir / "draft.md").write_text(md)
        return md

    papers = (lit.get("arxiv") or [])[:10] + (lit.get("semantic_scholar") or [])[:8]
    paper_lines = []
    for i, p in enumerate(papers, 1):
        t = p.get("title") or "?"
        abs_ = (p.get("abstract") or "")[:250]
        ref = p.get("arxiv_id") or p.get("doi") or ""
        paper_lines.append(f"[{i}] {t}\n    {abs_}\n    ref: {ref}")
    paper_ctx = "\n\n".join(paper_lines)

    hyp_text = ""
    if isinstance(hyp.get("hypotheses"), list):
        hyp_text = "\n".join(
            f"- {h.get('statement', '')}" for h in hyp["hypotheses"]
        )

    prompt = f"""Write a structured literature review on the project "{project['title']}".

Description: {project.get('description', '')}

You have {len(papers)} recent papers to synthesize and 3 working hypotheses to motivate.

Working hypotheses:
{hyp_text}

Papers:
{paper_ctx}

Write a 1500-word literature review in clean GitHub-flavored markdown with:
1. **Abstract** (~150 words)
2. **Background and motivation** (~300 words)
3. **Synthesis of cited work** (~600 words, cite using [N] inline numbering matching the order above)
4. **Open questions and proposed hypotheses** (~300 words)
5. **References** (numbered list matching inline cites)

Be concrete. Do not invent papers. Cite only from the list above. If a hypothesis isn't well-supported, say so."""

    response = llm_chat(prompt, max_tokens=4000)
    out_path = out_dir / "draft.md"
    out_path.write_text(response)
    log("draft", f"wrote draft.md ({len(response)} chars)")
    return response


# ─── Stage 4: publish (Slack) ────────────────────────────────────────────────
def {{profile.lateness.stakeholders.senderType}}_publish(project: dict, lit: dict, hyp: dict, draft_md: str, out_dir: Path) -> None:
    log("publish", "posting summary to Slack")
    hyp_lines = []
    if isinstance(hyp.get("hypotheses"), list):
        for i, h in enumerate(hyp["hypotheses"], 1):
            hyp_lines.append(f"{i}. {h.get('statement', '?')}")

    arxiv_n = len(lit.get("arxiv") or [])
    s2_n = len(lit.get("semantic_scholar") or [])

    msg = "\n".join(
        [
            f":microscope: *auto-research E2E* — `{project['id']}`",
            f"*{project['title']}*",
            f"_{project.get('description', '')}_",
            "",
            f"📚 *Literature*: arXiv {arxiv_n}, Semantic Scholar {s2_n}",
            f"🧠 *Hypotheses*:",
            *hyp_lines,
            f"✍️  *Draft*: {len(draft_md)} chars → `{out_dir / 'draft.md'}`",
            "",
            f"`{out_dir}`",
        ]
    )

    if DRY_RUN or not SLACK_TOKEN or not SLACK_CHANNEL:
        print(f"[no-token-or-dry] Slack: {msg[:300]}")
        return
    # Slack chat.postMessage caps at ~40000 chars; trim with note
    if len(msg) > 39000:
        msg = msg[:38900] + "\n... (truncated)"
    payload = json.dumps({"channel": SLACK_CHANNEL, "text": msg}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        if not body.get("ok"):
            log("publish", f"slack failed: {body}")


# ─── Main ────────────────────────────────────────────────────────────────────
def main() -> int:
    project = pick_project()
    log("init", f"project = {project['id']}")
    out_dir = WORKSPACE / project["id"] / TODAY
    out_dir.mkdir(parents=True, exist_ok=True)

    # Same-day idempotency: skip unless FORCE_RERUN
    summary_path = out_dir / "summary.json"
    if summary_path.exists() and not os.environ.get("FORCE_RERUN"):
        log("skip", f"already ran today ({summary_path}); set FORCE_RERUN=1 to re-run")
        return 0

    lit: dict = {}
    hyp: dict = {}
    draft_md: str = ""
    error: str | None = None
    try:
        lit = {{profile.lateness.stakeholders.senderType}}_literature(project, out_dir)
        time.sleep(1)
        hyp = {{profile.lateness.stakeholders.senderType}}_hypothesise(project, lit, out_dir)
        time.sleep(1)
        draft_md = {{profile.lateness.stakeholders.senderType}}_draft_paper(project, lit, hyp, out_dir)
        {{profile.lateness.stakeholders.senderType}}_publish(project, lit, hyp, draft_md, out_dir)
    except Exception as e:
        error = repr(e)
        log("error", error)

    summary = {
        "project": project["id"],
        "date": TODAY,
        "literature_count": lit.get("total", 0),
        "hypothesis_count": len(hyp.get("hypotheses", [])) if isinstance(hyp.get("hypotheses"), list) else 0,
        "draft_chars": len(draft_md),
        "out_dir": str(out_dir),
        "error": error,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    log("done", json.dumps(summary, ensure_ascii=False))
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
