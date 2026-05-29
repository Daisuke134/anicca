#!/usr/bin/env python3
"""homework-auto-draft.py — LLM-driven Quarto draft generation (Task #6).

End goal: the user does not touch edu-portal for the entire two-year
master's programme. This script closes the loop between
`homework-fetch.py` (knows what is due) and `homework-submit.py` (knows
how to upload + click 確定) by **generating the answer PDF itself**.

Pipeline (per outstanding homework in `~/.openclaw/workspace/naist/<slug>/homework-<today>.json`):

  1. Read the assignment's `kadai_content` (course question text) and
     `subject` / `subject_code`.
  2. If a lecture PDF lives in
     `~/.openclaw/workspace/naist/<slug>/homework/<class-slug>/lecture*.pdf`,
     pdftotext-extract it and include as context.
  3. Pull the user's `research-profile.json` so the LLM can match
     answers to the student's voice / interests.
  4. Call an OpenRouter model (cheap default: `deepseek/deepseek-v4-pro`,
     ~$0.08 per ~3k-token draft) with a structured prompt asking for a
     Quarto-flavoured Markdown answer. Fall back to
     `deepseek/deepseek-v4-flash` → `moonshot/kimi-k2.6` →
     `openai/gpt-5.4-mini` if the primary is unavailable.
  5. Write `~/.openclaw/workspace/naist/<slug>/homework/<class-slug>/report.qmd`,
     run `quarto render` → `report.pdf`.
  6. Write the draft JSON expected by `homework-submit.py`:
       {
         "submission_url":  <from homework-<today>.json>,
         "thread_id":       <subject_code-kadai_name slug>,
         "deadline":        <parsed from teishutsu_period>,
         "submit_at":       <deadline minus 1 day>,
         "pdf_path":        "<abs path to report.pdf>",
         "submitted":       false
       }
     into `~/.openclaw/workspace/naist/<slug>/drafts/<class-slug>/<ts>.json`.

Cron: `0 8 * * *` Asia/Tokyo (runs an hour after `naist-homework-fetch`).
`naist-homework-submit` at 14:00 JST then picks up any drafts whose
`submit_at <= today`.

Status: skeleton. The LLM-call body is left as TODO until OpenRouter
credentials are wired into `~/.openclaw/.env` (see `.env.example`
`OPENROUTER_API_KEY` / `HOMEWORK_DRAFT_MODEL`). Until then, the script
detects outstanding homeworks and writes a placeholder draft JSON so the
cron pipeline can be exercised end-to-end with hand-rendered PDFs.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SLUG = os.environ.get("SLUG", "")
WORKSPACE = Path.home() / ".openclaw" / "workspace" / "naist"
STATE_ROOT = Path.home() / ".openclaw" / "state" / "naist"
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = os.environ.get("HOMEWORK_DRAFT_MODEL", "deepseek/deepseek-v4-pro")
LANG = os.environ.get("HOMEWORK_DRAFT_LANGUAGE", "en")  # "en" or "ja"
FALLBACKS = [
    "deepseek/deepseek-v4-flash",
    "moonshot/kimi-k2.6",
    "openai/gpt-5.4-mini",
]


def fail(msg: str, code: int = 1) -> None:
    print(f"homework-auto-draft[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def parse_deadline(period: str) -> date | None:
    """Extract the END date from a string like '2026/05/13(水) 00:00～2026/05/31(日) 00:00'."""
    m = re.findall(r"(\d{4})/(\d{2})/(\d{2})", period or "")
    if len(m) >= 2:
        y, mo, d = m[-1]
        return date(int(y), int(mo), int(d))
    return None


def find_lecture_pdfs(class_slug: str) -> list[Path]:
    d = WORKSPACE / SLUG / "homework" / class_slug
    if not d.exists():
        return []
    return sorted(d.glob("lecture*.pdf")) + sorted(d.glob("Assignment*.pdf"))


def pdf_text(p: Path) -> str:
    """Use pdftotext if available; otherwise return empty so the LLM works with what it has."""
    try:
        r = subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def call_llm(prompt: str) -> str | None:
    """Single OpenRouter call with fallbacks. Returns markdown or None on hard failure.

    Body TODO: implement with urllib/requests when OPENROUTER_API_KEY is set.
    Today this is a skeleton — outputs a placeholder draft and lets a human
    hand-edit. Cron exercises the rest of the pipeline so the auto-submit
    path is proven before LLM is wired in.
    """
    if not OR_KEY:
        print(
            "[skel] OPENROUTER_API_KEY not set — emitting placeholder answer so "
            "homework-submit can still be tested with a hand-rendered PDF.",
            file=sys.stderr,
        )
        return None
    # TODO: POST https://openrouter.ai/api/v1/chat/completions with
    #   {model: MODEL, messages: [{role: user, content: prompt}], temperature: 0.2}
    # then iterate over FALLBACKS on 429/5xx.
    return None


def build_prompt(hw: dict, lecture_excerpts: list[str], research_profile: dict) -> str:
    persona = json.dumps(research_profile, ensure_ascii=False, indent=2) if research_profile else "{}"
    lec = "\n\n---\n\n".join(lecture_excerpts) if lecture_excerpts else "(no lecture material attached)"
    return f"""You are answering a NAIST graduate-school assignment on behalf of the
student described below. Write the answer in {LANG} (English if LANG=en,
日本語 if LANG=ja). Output a complete Quarto Markdown document with:

  - YAML front-matter (title, author from student.user_full_name_romaji,
    date today, format pdf, pdf-engine xelatex, Hiragino Kaku Gothic Pro
    main font, amsmath + amssymb).
  - Clear sections, math typeset with \\(\\) or display $$, tables when
    helpful, no chit-chat.
  - At the very end of the file, a one-paragraph "Note" only if the
    submission is past the original deadline (use the lecture's stated
    late-submission policy, do not invent one).

ASSIGNMENT METADATA
  Course code:  {hw.get('subject_code', '?')}
  Course name:  {hw.get('subject', '?')}
  Assignment:   {hw.get('kadai_name', '?')}
  Submission window: {hw.get('teishutsu_period', '?')}
  Method: {hw.get('teishutsu_method', '?')}

ASSIGNMENT TEXT
\"\"\"
{hw.get('kadai_content', '(missing)')}
\"\"\"

LECTURE MATERIAL EXCERPTS (use only what is needed)
\"\"\"
{lec[:30000]}
\"\"\"

STUDENT RESEARCH PROFILE (use to match voice / depth)
{persona}

Output ONLY the .qmd file content. Do not wrap in code fences.
"""


def render_quarto(qmd_path: Path) -> Path | None:
    pdf = qmd_path.with_suffix(".pdf")
    r = subprocess.run(
        ["quarto", "render", str(qmd_path), "--to", "pdf"],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        print(f"  quarto render failed: {r.stderr[:300]}", file=sys.stderr)
        return None
    return pdf if pdf.exists() else None


def write_draft_json(hw: dict, pdf_path: Path | None, deadline: date | None, drafts_root: Path) -> Path:
    class_slug = slugify(hw.get('subject_code') or hw.get('subject') or 'unknown')
    name_slug = slugify(hw.get('kadai_name') or hw.get('label') or 'assignment')
    out_dir = drafts_root / class_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    out = out_dir / f"{name_slug}-{ts}.json"
    submit_at = (deadline - timedelta(days=1)).isoformat() if deadline else date.today().isoformat()
    draft = {
        "submission_url": hw.get("url"),
        "thread_id": f"{class_slug}/{name_slug}",
        "subject": hw.get("subject"),
        "subject_code": hw.get("subject_code"),
        "kadai_name": hw.get("kadai_name"),
        "deadline": deadline.isoformat() if deadline else None,
        "submit_at": submit_at,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "auto_drafted": pdf_path is not None,
        "submitted": False,
    }
    out.write_text(json.dumps(draft, ensure_ascii=False, indent=2))
    return out


def main() -> int:
    if not SLUG:
        fail("SLUG env required")

    today = date.today().isoformat()
    fetched = WORKSPACE / SLUG / f"homework-{today}.json"
    if not fetched.exists():
        # Fall back to the most recent fetch JSON
        candidates = sorted((WORKSPACE / SLUG).glob("homework-*.json"))
        if not candidates:
            print(f"homework-auto-draft[{SLUG}]: no homework-*.json found — run homework-fetch first")
            return 0
        fetched = candidates[-1]
    snapshot = json.loads(fetched.read_text())
    homeworks = snapshot.get("homeworks", [])
    if not homeworks:
        print(f"homework-auto-draft[{SLUG}]: 0 homeworks in {fetched.name}")
        return 0

    research_profile_path = STATE_ROOT / SLUG / "research-profile.json"
    research_profile = json.loads(research_profile_path.read_text()) if research_profile_path.exists() else {}

    drafts_root = WORKSPACE / SLUG / "drafts"
    drafts_root.mkdir(parents=True, exist_ok=True)
    results = []

    for hw in homeworks:
        class_slug = slugify(hw.get('subject_code') or hw.get('subject') or 'unknown')
        class_dir = WORKSPACE / SLUG / "homework" / class_slug
        class_dir.mkdir(parents=True, exist_ok=True)

        lecture_excerpts = [pdf_text(p)[:20000] for p in find_lecture_pdfs(class_slug)]
        deadline = parse_deadline(hw.get("teishutsu_period", ""))

        prompt = build_prompt(hw, lecture_excerpts, research_profile)
        qmd_text = call_llm(prompt)
        pdf_path: Path | None = None

        if qmd_text:
            qmd = class_dir / "report.qmd"
            qmd.write_text(qmd_text)
            pdf_path = render_quarto(qmd)

        draft_json = write_draft_json(hw, pdf_path, deadline, drafts_root)
        results.append({
            "subject_code": hw.get("subject_code"),
            "kadai_name": hw.get("kadai_name"),
            "deadline": deadline.isoformat() if deadline else None,
            "auto_drafted": pdf_path is not None,
            "draft_json": str(draft_json),
        })

    out = WORKSPACE / SLUG / f"homework-auto-draft-{today}.json"
    out.write_text(json.dumps({"slug": SLUG, "run_at": today, "results": results}, ensure_ascii=False, indent=2))
    print(f"homework-auto-draft[{SLUG}]: processed {len(results)} homeworks (auto-drafted={sum(1 for r in results if r['auto_drafted'])}) → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
