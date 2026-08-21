#!/usr/bin/env python3
"""citation-strip — collapse inline (出典: [...](...)) citations into a final 出典 block.

Per PLAYBOOK rule 26 (= ALL citations in ONE final 出典 block, no inline noise).

Usage:
    python3 citation-strip.py < input.md > output.md
    python3 citation-strip.py input.md output.md
    python3 citation-strip.py --in-place input.md   # writes back

What it does (in order):
  1. Collects every (出典: [LABEL](URL)) match, preserves first-seen order,
     deduplicates by URL.
  2. Removes every inline (出典: ...) from the body.
  3. Collapses orphaned punctuation introduced by the removal:
       。。 -> 。
       、、 -> 、
       trailing whitespace before 。 or 、
  4. Appends a new "## 出典" block at the end of the document with the
     deduplicated URL list (preserves Markdown link format).

If the document already has a "## 出典" h2, the new URLs are MERGED into
the existing block (dedup by URL), and no duplicate header is added.

Why a shared script: every Writer Agent article we ship runs through this
cleanup. Keeping the regex + dedup logic in one place stops the per-script
drift (= the bug that left `ほとんどです。。` on the Frank note draft).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CITATION_RE = re.compile(r"（出典:\s*[^）]*）")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SOURCE_HEADER_RE = re.compile(r"^(##\s*出典\s*)$", re.MULTILINE)


def extract_pairs(citations: list[str]) -> list[tuple[str, str]]:
    """Pull (label, url) pairs from collected citation strings; dedup by url, preserve order."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for c in citations:
        for label, url in LINK_RE.findall(c):
            if url in seen:
                continue
            seen.add(url)
            out.append((label, url))
    return out


def existing_block_urls(body: str) -> set[str]:
    """If body already has a `## 出典` block, return the URLs already present in it."""
    m = SOURCE_HEADER_RE.search(body)
    if not m:
        return set()
    tail = body[m.end():]
    # next h2 ends the 出典 block
    next_h2 = re.search(r"^## ", tail, re.MULTILINE)
    block = tail[: next_h2.start()] if next_h2 else tail
    return {url for _, url in LINK_RE.findall(block)}


def render_source_block(pairs: list[tuple[str, str]]) -> str:
    lines = ["", "---", "", "## 出典", ""]
    for label, url in pairs:
        lines.append(f"- [{label}]({url})")
    lines.append("")
    return "\n".join(lines)


def strip_and_collect(body: str) -> tuple[str, list[tuple[str, str]]]:
    citations = CITATION_RE.findall(body)
    pairs = extract_pairs(citations)
    cleaned = CITATION_RE.sub("", body)
    # collapse orphans introduced by the removal
    cleaned = re.sub(r"。。+", "。", cleaned)
    cleaned = re.sub(r"、、+", "、", cleaned)
    # collapse double-space and trailing whitespace before sentence-final marks
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\s+(?=[。、])", "", cleaned)
    # collapse triple+ blank lines down to two
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, pairs


def merge_into_block(body_clean: str, new_pairs: list[tuple[str, str]]) -> str:
    """If a 出典 block already exists, merge new pairs into it (dedup). Else append a new one."""
    if not new_pairs:
        return body_clean.rstrip() + "\n"
    if SOURCE_HEADER_RE.search(body_clean):
        existing = existing_block_urls(body_clean)
        to_add = [(label, url) for label, url in new_pairs if url not in existing]
        if not to_add:
            return body_clean.rstrip() + "\n"
        # append after the LAST line of the existing block, before any next h2
        m = SOURCE_HEADER_RE.search(body_clean)
        head = body_clean[: m.end()]
        tail = body_clean[m.end():]
        next_h2 = re.search(r"^## ", tail, re.MULTILINE)
        if next_h2:
            block_existing = tail[: next_h2.start()].rstrip()
            after = tail[next_h2.start():]
        else:
            block_existing = tail.rstrip()
            after = ""
        new_lines = "\n".join(f"- [{l}]({u})" for l, u in to_add)
        merged = f"{head}\n{block_existing}\n{new_lines}\n\n{after}".rstrip() + "\n"
        return merged
    return body_clean.rstrip() + render_source_block(new_pairs)


def transform(body: str) -> str:
    cleaned, pairs = strip_and_collect(body)
    return merge_into_block(cleaned, pairs)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("input", nargs="?", help="input markdown path (- for stdin)")
    p.add_argument("output", nargs="?", help="output markdown path (- for stdout)")
    p.add_argument("--in-place", action="store_true", help="overwrite input file")
    p.add_argument("--report", action="store_true", help="emit citation count summary to stderr")
    args = p.parse_args(argv)

    if args.in_place:
        if not args.input or args.input == "-":
            print("--in-place requires a file path", file=sys.stderr)
            return 2
        src = Path(args.input).read_text(encoding="utf-8")
    elif args.input and args.input != "-":
        src = Path(args.input).read_text(encoding="utf-8")
    else:
        src = sys.stdin.read()

    cleaned, pairs = strip_and_collect(src)
    out = merge_into_block(cleaned, pairs)

    if args.report:
        print(f"[citation-strip] inline (出典: ...) removed: {len(CITATION_RE.findall(src))}", file=sys.stderr)
        print(f"[citation-strip] unique URLs in final block: {len(pairs)}", file=sys.stderr)

    if args.in_place:
        Path(args.input).write_text(out, encoding="utf-8")
    elif args.output and args.output != "-":
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
