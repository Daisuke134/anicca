#!/usr/bin/env python3
"""Generate confirmed-selections.json from a skill's SKILL.md.

Deterministic — no LLM. Reads YAML frontmatter + first markdown section to
build title (<=50 chars), short description (<=500 chars), details markdown,
and routes to the right Capafy category by keyword heuristic.
"""

import json
import re
import sys
from pathlib import Path


CATEGORY_KEYWORDS = {
    "Engineering": ["api", "cli", "code", "git", "deploy", "build", "test", "debug",
                    "framework", "library", "skill", "agent", "automation",
                    "package", "publisher", "developer", "compile"],
    "Marketing": ["tiktok", "instagram", "twitter", "x.com", "reel", "viral",
                  "campaign", "ad ", "ads", "seo", "blog", "post", "social",
                  "engagement", "follower", "audience"],
    "Writing": ["article", "essay", "translate", "humanize", "ghostwrit",
                "blog post", "newsletter", "edit", "proofread", "tone"],
    "Productivity": ["calendar", "schedule", "task", "todo", "reminder",
                     "notion", "email inbox", "meeting", "note", "habit"],
    "Product": ["onboarding", "paywall", "conversion", "retention", "growth",
                "experiment", "a/b", "user research"],
}


def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    out: dict[str, str] = {}
    key = None
    buf: list[str] = []
    for line in block.split("\n"):
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.*)$", line)
        if m:
            if key is not None:
                out[key] = "\n".join(buf).strip().strip('"\'')
            key = m.group(1)
            buf = [m.group(2)]
        else:
            buf.append(line)
    if key is not None:
        out[key] = "\n".join(buf).strip().strip('"\'')
    return out


def _strip_inline(s: str) -> str:
    """Replace literal newlines + collapse whitespace so a single-paragraph
    short description fits Capafy's textarea cleanly."""
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    # cut at last sentence boundary before limit
    cut = s[:limit].rstrip()
    last = max(cut.rfind(". "), cut.rfind("。"), cut.rfind("! "), cut.rfind("? "))
    if last > limit * 0.5:
        return cut[: last + 1]
    return cut[: limit - 1] + "…"


def pick_category(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in kws if kw in lower)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "Engineering"


def build(skill_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    raw = skill_md.read_text(encoding="utf-8")
    fm = _frontmatter(raw)
    name = fm.get("name") or skill_dir.name
    desc_fm = _strip_inline(fm.get("description", ""))

    # Title generation:
    # H1 from SKILL.md is often a section heading ("How to run", "Usage")
    # rather than a real product title. Trust it only if it doesn't look
    # like a how-to/installation heading. Otherwise prefer a humanized
    # skill name + a short tagline from the frontmatter description.
    body = raw.split("\n---", 1)[-1]
    h1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    h1_text = h1.group(1).strip() if h1 else ""
    bad_h1 = re.search(
        r"(?i)\b(how to (run|use|install)|usage|installation|quickstart|getting started|setup|run prerequisites)\b",
        h1_text,
    )

    name_clean = name.replace("-", " ").replace("_", " ").strip().title()
    # one short tagline (first sentence of description, ≤6 words)
    first_sentence = re.split(r"[.。!?！？]", desc_fm, 1)[0].strip()
    tagline = " ".join(first_sentence.split()[:6])

    if h1_text and not bad_h1 and len(h1_text) <= 50:
        title = h1_text
    else:
        candidate = f"{name_clean} — {tagline}" if tagline else name_clean
        title = candidate if len(candidate) <= 50 else name_clean[:50]

    # short: from frontmatter description, trim to 480 (leave headroom under 500)
    short = _truncate(desc_fm or h1_text, 480)

    # details: full SKILL.md body (post-frontmatter), capped at 80000 to stay
    # under Capafy's 100000 limit with margin
    details = body.strip()
    details = _truncate(details, 80000)

    category = pick_category(raw)

    return {
        "title": title,
        "description": short,
        "details": details,
        "category": category,
        "skills": [
            {
                "path": f".claude/skills/{name}",
                "name": name,
                "purpose": short,
            }
        ],
        "plugins": [],
        "crons": [],
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: selections_from_skill_md.py <skill_dir>", file=sys.stderr)
        return 2
    skill_dir = Path(argv[1]).expanduser().resolve()
    sel = build(skill_dir)
    # IMPORTANT: capafy publish-init expects `description` for the agent card,
    # and we drop our internal extras (details + category) into the side-channel
    # files used by drive_checkpoint1.py — the publisher rejects unknown keys.
    side = sel.pop("details")
    cat = sel.pop("category")
    # Write the auxiliary file OUTSIDE both capafy-publisher/.temp (which
    # publish-init --reset-local-state wipes) AND capafy-autopublish/ itself
    # (which gets staged into the published bundle — Capafy then rejects
    # ship with "creator-local paths"). ~/.cache survives between runs and
    # is excluded from any skill bundle.
    aux = Path.home() / ".cache" / "anicca-capafy" / "selections-aux.json"
    aux.parent.mkdir(parents=True, exist_ok=True)
    aux.write_text(json.dumps({"details": side, "category": cat}, ensure_ascii=False))
    print(json.dumps(sel, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
