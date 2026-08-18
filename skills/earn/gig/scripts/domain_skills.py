#!/usr/bin/env python3
"""Emit the domain-skill text a step must know BEFORE it touches the marketplace.

Why this exists separately from lane_lessons.py: lessons are *observations* the prompt
explicitly labels "never override this step's ownership". Domain skills are the opposite —
they are operating facts about the site and the browser that were paid for once, in a
session that stalled until someone opened the real page and looked. A lane that does not
know them repeats the stall. On 2026-08-04 the apply/deliver lanes burned 24 passes on one
order because nobody knew the buyer's attachments arrive in the DM thread, not the talkroom.

Written by the harness, for the harness. When a step gets stuck and the fix is a site fact,
append it here in the same pass — not after the job, because by then it is forgotten.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "domain-skills"

# Which SECTIONS each step needs, by "## heading" of the skill file. Shipping every file
# to every lane doubles the prompt for facts the lane cannot use: B2 never delivers, so it
# does not need the delivery limits; PAID_WORK never applies, so it does not need the
# withdrawal path. The floor is charged on every call, so only what the lane can act on.
BY_STEP: dict[str, dict[str, tuple[str, ...]]] = {
    "B0": {"browser": ("クリックが効かない時", "要素が見つからない時", "共有ブラウザ", "セッション"),
           "coconala": ("評価", "出品"),
           "failure-lessons": ("B0",)},
    "B1": {"browser": ("要素が見つからない時", "レンダラが固まった時", "共有ブラウザ", "セッション",
                       "認証情報が無い時"),
           "coconala": ("会話を読む", "取引と提案", "評価", "納品の制約"),
           "failure-lessons": ("B1",)},
    "B2": {"browser": ("クリックが効かない時", "要素が見つからない時", "共有ブラウザ"),
           "coconala": ("応募",),
           "failure-lessons": ("B2",)},
    "PROFILE": {"browser": ("要素が見つからない時", "共有ブラウザ", "セッション"),
                "coconala": (),
                "failure-lessons": ("PROFILE",)},
    "PAID_WORK": {"browser": ("クリックが効かない時", "要素が見つからない時", "レンダラが固まった時",
                              "入力できないウィジェット", "セッション", "認証情報が無い時"),
                  "coconala": ("会話を読む", "数字の読み違い", "納品の制約"),
                  "failure-lessons": ("PAID_WORK",)},
    "REPLY": {"browser": ("要素が見つからない時", "共有ブラウザ"),
              "coconala": ("会話を読む", "評価"),
              "failure-lessons": ("REPLY",)},
    "LEARN": {"coconala": ("会話を読む", "応募", "評価"),
              "failure-lessons": ("LEARN",)},
}

# failure-lessons.md is not hand-curated like browser.md/coconala.md -- it is regenerated
# every pass by failure_lessons.py (gig_pass.sh on_exit trap) from ~/gig/pass-failures.jsonl
# counts. load()/sections() already treat any *.md in SKILL_DIR the same way, so wiring it
# in only needed this BY_STEP entry, no change to the extraction path.


def load(name: str) -> str:
    path = SKILL_DIR / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def sections(body: str, wanted: tuple[str, ...]) -> str:
    """Keep only the requested '## ' blocks, in file order."""
    if not wanted:
        return ""
    keep: list[str] = []
    current: list[str] = []
    taking = False
    for line in body.splitlines():
        if line.startswith("## "):
            if taking and current:
                keep.append("\n".join(current).rstrip())
            head = line[3:].strip()
            taking = any(w in head for w in wanted)
            current = [line] if taking else []
            continue
        if taking:
            current.append(line)
    if taking and current:
        keep.append("\n".join(current).rstrip())
    return "\n".join(keep)


def fragment(step: str, limit: int) -> str:
    plan = BY_STEP.get(step.upper())
    if not plan:
        return ""
    bodies = []
    for name, wanted in plan.items():
        picked = sections(load(name), wanted)
        if picked:
            bodies.append(f"[{name}]\n{picked}")
    if not bodies:
        return ""
    text = "\n\n".join(bodies)
    if limit and len(text) > limit:
        text = text[:limit].rsplit("\n", 1)[0]
    return (
        " Site and browser facts this lane already paid for (operating knowledge, not"
        " optional advice — a lane that ignores these repeats a stall that has already"
        " cost real passes). Follow them unless the live page contradicts them, and when"
        " it does, say so in your evidence so they can be corrected:\n" + text + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("--limit", type=int, default=int(0))
    args = ap.parse_args(argv)
    out = fragment(args.step, args.limit)
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
