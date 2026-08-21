#!/usr/bin/env python3
"""Convert Markdown constructs that Substack's draft renderer breaks.

Substack currently collapses GFM tables into one paragraph containing literal
pipe characters.  Replace each table with a compact heading plus definition
bullets, using only Markdown structures the editor renders reliably.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DELIMITER_CELL = re.compile(r"^:?-{3,}:?$")


def _cells(line: str) -> list[str]:
    stripped = line.rstrip("\r\n").strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def _is_delimiter(line: str, width: int) -> bool:
    cells = _cells(line)
    return len(cells) == width and all(DELIMITER_CELL.fullmatch(cell) for cell in cells)


def _render_table(headers: list[str], rows: list[list[str]], newline: str) -> list[str]:
    rendered = [f"**{' / '.join(headers)}**{newline}"]
    for row in rows:
        if len(headers) == 2:
            rendered.append(f"- **{row[0]}:** {row[1]}{newline}")
        else:
            parts = [f"**{header}:** {value}" for header, value in zip(headers, row)]
            rendered.append(f"- {'; '.join(parts)}{newline}")
    return rendered


def convert_tables(markdown: str) -> str:
    lines = markdown.splitlines(keepends=True)
    if not lines:
        return markdown

    newline = "\r\n" if "\r\n" in markdown else "\n"
    output: list[str] = []
    index = 0
    while index < len(lines):
        headers = _cells(lines[index]) if "|" in lines[index] else []
        if (
            len(headers) >= 2
            and index + 1 < len(lines)
            and _is_delimiter(lines[index + 1], len(headers))
        ):
            rows: list[list[str]] = []
            cursor = index + 2
            while cursor < len(lines) and "|" in lines[cursor]:
                row = _cells(lines[cursor])
                if len(row) != len(headers):
                    break
                rows.append(row)
                cursor += 1

            if rows:
                output.extend(_render_table(headers, rows, newline))
                index = cursor
                continue

        output.append(lines[index])
        index += 1
    return "".join(output)


def strip_frontmatter_and_leading_h1(markdown: str) -> str:
    markdown = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", markdown, count=1, flags=re.S)
    return re.sub(r"^#\s+.+$", "", markdown, count=1, flags=re.M)


def preprocess(markdown: str, *, strip_frontmatter_h1: bool = False) -> str:
    if strip_frontmatter_h1:
        markdown = strip_frontmatter_and_leading_h1(markdown)
    return convert_tables(markdown)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown_file", type=Path)
    parser.add_argument("--strip-frontmatter-h1", action="store_true")
    args = parser.parse_args()
    source = args.markdown_file.read_text(encoding="utf-8")
    sys.stdout.write(preprocess(source, strip_frontmatter_h1=args.strip_frontmatter_h1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
