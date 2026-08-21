#!/usr/bin/env python3
"""make-free-version — machine-assemble a "free version" teaser from a paid article.

Shape proven by hand at ~/.cloak/note-work/2026-07-12-agent-economy-jp-x-free.md
(original: docs/articles/2026-07-12-how-to-build-the-agent-economy-jp.md):
  1. original H1 title, verbatim
  2. the original body, TRUNCATED at a paywall line
  3. "## まとめ" + 3-5 bullets (the free part's own takeaways)
  4. the original "## Sources"/"## 出典" section, verbatim, if the original had one --
     brought forward regardless of where the cut landed (spec #47 fix, 2026-07-16: this
     section almost always sits past the paywall and was silently dropped, shipping free
     versions with real numbers and zero citations for them)
  5. "---"
  6. one plain paragraph (not a heading): "この記事は無料版です。完全版（note・
     {price}円買い切り）には、この続き（{paid_contents}）が入っています。"
  7. the note URL, alone, as the last line

Judgment this script does NOT make (caller must supply it, per SKILL.md rule):
  --summary-file   the 3-5 まとめ bullets (what's worth keeping in the free part)
  --paid-contents  the exact naming of what's behind the paywall
Everything else — where to cut, how to assemble, what to reject — is mechanical.

Where the cut lands: copied from scripts/note-publish/publish-paid.py's own algorithm
(env PAYWALL_AFTER_CHARS, default 2500 — "Re-measure it, do not trust this number").
That script walks note.com's RENDERED DOM and stops at the first paragraph-level
「ラインをこの場所に変更」 button once accumulated leaf-text chars >= AFTER — there is
no live DOM here, so this script re-implements the same accumulate-then-cut idea over
the raw markdown: walk headings / list bullets / sentences (split on 。, which is what
lets a cut land mid-paragraph the way the hand-made sample does) in document order,
skipping ```code``` fences entirely from BOTH the character count and as cut candidates
(so a cut can never land inside one — the guard the caller asked for falls out of this
for free, it does not need special-casing). --after-chars overrides the default per
article, same as PAYWALL_AFTER_CHARS does for the real paywall line.

MEASURED 2026-07-16: for the reference article, the hand-made sample's cut lands at
~3,609 plain-text chars in (sentence "...誰も担保していません。"), not at the 2,500
default. The 2,500 default from publish-paid.py is note.com's own paywall-placement
heuristic for THIS article's actual sale; it is not guaranteed to match wherever a
human chose to end a companion free teaser for X — that is a separate editorial call.
Pass --after-chars explicitly when the caller wants to match a specific target length.

Guards (violation = non-zero exit + FATAL to stderr):
  - no teaser H2 in the output (any "#"x2-6 heading containing 続き)
  - no full-width double dash ("——") anywhere in the output
  - summary bullets: 3-5 (from --summary-file, lines starting with "-" or "*")
  - output's last non-empty line == --note-url exactly
  - --note-url / --price / --paid-contents / --summary-file are all required

CLI:
    python3 make-free-version.py --markdown-file <original.md> --note-url <url> \
        --price <int> --paid-contents "<what's behind the paywall>" \
        --summary-file <bullets.md> --out <output.md> [--after-chars 2500]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_AFTER_CHARS = 2500
FOOTER_TEMPLATE = (
    "この記事は無料版です。完全版（note・{price:,}円買い切り）には、"
    "この続き（{paid_contents}）が入っています。"
)


def fatal(msg: str) -> "None":
    raise SystemExit(f"FATAL: {msg}")


def plain(s: str) -> str:
    """Strip markdown syntax markers, keep what a reader actually sees."""
    s = re.sub(r"^#{1,6}\s*", "", s)
    s = re.sub(r"^[-*]\s*", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    return s


def split_sentences(text: str) -> list[str]:
    """Split on the Japanese full stop, keeping it attached to each sentence."""
    text = text.strip()
    if not text:
        return []
    return [s for s in re.findall(r"[^。]*。|[^。]+$", text) if s.strip()]


def parse_segments(body: str) -> list[dict]:
    """Walk the markdown body (title line already removed) into ordered segments.

    Segment types: 'code' (raw, atomic, never a cut candidate, 0 chars),
    'hr' (raw '---'), 'heading' (raw + counted text), 'bullet' (one list line,
    raw + counted text), 'sentence' (one sentence out of a paragraph, raw + counted
    text; consecutive sentences from the same paragraph share a 'para_id' so the
    truncated remainder can be re-joined without inserting one paragraph per sentence).
    """
    lines = body.split("\n")
    segs: list[dict] = []
    i, n = 0, len(lines)
    para_buf: list[str] = []
    para_id = 0

    def flush_para():
        nonlocal para_id
        if not para_buf:
            return
        text = " ".join(l.strip() for l in para_buf if l.strip())
        para_buf.clear()
        # keep the RAW text (bold markers etc. intact) — plain() is only for counting
        for sent in split_sentences(text):
            segs.append({"type": "sentence", "raw": sent, "para_id": para_id})
        para_id += 1

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_para()
            code_lines = [line]
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < n:
                code_lines.append(lines[i])
                i += 1
            segs.append({"type": "code", "raw": "\n".join(code_lines)})
            continue
        if stripped == "":
            flush_para()
            i += 1
            continue
        if stripped == "---":
            flush_para()
            segs.append({"type": "hr", "raw": line})
            i += 1
            continue
        if re.match(r"^#{1,6}\s", stripped):
            flush_para()
            segs.append({"type": "heading", "raw": line})
            i += 1
            continue
        if re.match(r"^[-*]\s", stripped):
            flush_para()
            segs.append({"type": "bullet", "raw": line})
            i += 1
            continue
        para_buf.append(line)
        i += 1
    flush_para()
    return segs


def cut_body(body: str, after_chars: int) -> tuple[str, dict]:
    """Return (truncated markdown body, debug info) cut at the first counted unit
    whose cumulative chars >= after_chars. Code fences count 0 and are only kept
    whole (never the cut point itself)."""
    segs = parse_segments(body)
    kept: list[dict] = []
    total = 0
    cut_at = None
    for seg in segs:
        if seg["type"] == "code":
            if cut_at is not None:
                break
            kept.append(seg)
            continue
        total += len(plain(seg["raw"]))
        kept.append(seg)
        if total >= after_chars:
            cut_at = total
            break

    # reconstruct markdown from kept segments: consecutive sentences of the same
    # paragraph rejoin into one line, consecutive bullets stay a tight list (no
    # blank line between bullets, matching the source's own formatting).
    out_lines: list[str] = []
    idx = 0
    while idx < len(kept):
        seg = kept[idx]
        if seg["type"] == "sentence":
            pid = seg["para_id"]
            buf = []
            while idx < len(kept) and kept[idx]["type"] == "sentence" and kept[idx]["para_id"] == pid:
                buf.append(kept[idx]["raw"])
                idx += 1
            out_lines.append("".join(buf))
            out_lines.append("")
            continue
        if seg["type"] == "bullet":
            while idx < len(kept) and kept[idx]["type"] == "bullet":
                out_lines.append(kept[idx]["raw"])
                idx += 1
            out_lines.append("")
            continue
        out_lines.append(seg["raw"])
        out_lines.append("")
        idx += 1

    free_tail = kept[-1]["raw"][-80:] if kept else ""
    return "\n".join(out_lines).rstrip() + "\n", {
        "free_chars": total,
        "free_ends_with": free_tail,
        "cut": cut_at is not None,
    }


SOURCES_HEADING_RE = re.compile(r"^(#{1,6})\s*(Sources|出典)\s*$", re.IGNORECASE)


def extract_sources_section(body: str) -> "str | None":
    """Find a `## Sources` / `## 出典` heading (any level -- real drafts use both ## and
    ### for this section) in the ORIGINAL, untruncated body and return its raw text
    verbatim: the heading line through the line before the next heading of the same or
    shallower level, or end of document. Returns None if no such section exists.
    Deliberately an EXACT heading-text match (no substring/fuzzy matching) so an
    unrelated heading is never mistaken for the citations block.

    spec #47 (2026-07-16, discovered by the X-en eval gate FAILing on uncited real
    numbers): this section almost always lives past the paywall cut, so cut_body()
    silently drops it and every free version shipped with earned numbers and zero
    citations for them.
    """
    lines = body.split("\n")
    start = level = None
    for i, line in enumerate(lines):
        m = SOURCES_HEADING_RE.match(line.strip())
        if m:
            start, level = i, len(m.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        hm = re.match(r"^(#{1,6})\s", lines[j].strip())
        if hm and len(hm.group(1)) <= level:
            end = j
            break
    return "\n".join(lines[start:end]).rstrip()


def load_summary(path: Path) -> list[str]:
    bullets = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if re.match(r"^[-*]\s+", s):
            bullets.append(re.sub(r"^[-*]\s+", "", s))
    return bullets


def check_no_teaser_heading(text: str) -> None:
    for line in text.splitlines():
        if re.match(r"^#{2,6}\s", line.strip()) and "続き" in line:
            fatal(f"teaser H2 found in output: {line!r}")


def check_no_fullwidth_dash(text: str) -> None:
    if "——" in text:
        fatal("output contains full-width double dash (——)")


def build(args: argparse.Namespace) -> str:
    src = Path(args.markdown_file).read_text(encoding="utf-8")
    lines = src.split("\n")
    title_line = None
    body_start = 0
    if lines and re.match(r"^#\s+", lines[0].strip()):
        title_line = lines[0]
        body_start = 1
    body = "\n".join(lines[body_start:])

    truncated, debug = cut_body(body, args.after_chars)
    if not debug["cut"]:
        fatal(
            f"after_chars={args.after_chars} exceeds the whole document "
            f"({debug['free_chars']} chars total) — nothing would be paid"
        )

    # spec #47 fix: bring the whole Sources/出典 section forward regardless of where the
    # cut landed. Picking only the citations that back numbers actually quoted in the
    # free part is not something this script can judge reliably, so all of it comes
    # along (citations are not a thing a reader can have too many of). Skip re-adding it
    # if the cut happened to already land past it (rare, but then it is already verbatim
    # inside `truncated` and adding it again would duplicate the section).
    sources_section = extract_sources_section(body)
    if sources_section and sources_section.splitlines()[0].strip() in truncated:
        sources_section = None

    bullets = load_summary(Path(args.summary_file))
    if not (3 <= len(bullets) <= 5):
        fatal(f"summary must have 3-5 bullets, got {len(bullets)}")

    parts = []
    if title_line:
        parts.append(title_line)
        parts.append("")
    parts.append(truncated.rstrip())
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## まとめ")
    parts.append("")
    for b in bullets:
        parts.append(f"- {b}")
    parts.append("")
    if sources_section:
        parts.append(sources_section)
        parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(
        FOOTER_TEMPLATE.format(price=args.price, paid_contents=args.paid_contents)
    )
    parts.append("")
    parts.append(args.note_url)
    parts.append("")

    out = "\n".join(parts)
    out = re.sub(r"\n{3,}", "\n\n", out).rstrip() + "\n"

    check_no_teaser_heading(out)
    check_no_fullwidth_dash(out)

    last_nonempty = [l for l in out.splitlines() if l.strip()][-1].strip()
    if last_nonempty != args.note_url.strip():
        fatal(f"last line must be the note URL, got {last_nonempty!r}")

    print(f"FREE_CHARS={debug['free_chars']}", file=sys.stderr)
    print(f"FREE_ENDS_WITH={debug['free_ends_with']!r}", file=sys.stderr)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--markdown-file", required=True)
    p.add_argument("--note-url")
    p.add_argument("--price", type=int)
    p.add_argument("--paid-contents")
    p.add_argument("--summary-file")
    p.add_argument("--out", required=True)
    p.add_argument("--after-chars", type=int, default=DEFAULT_AFTER_CHARS)
    args = p.parse_args(argv)

    if not args.note_url:
        fatal("--note-url is required")
    if args.price is None:
        fatal("--price is required")
    if not args.paid_contents:
        fatal("--paid-contents is required")
    if not args.summary_file:
        fatal("--summary-file is required")

    out = build(args)
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"WROTE={args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
