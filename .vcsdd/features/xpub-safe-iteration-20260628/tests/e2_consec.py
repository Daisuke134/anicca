#!/usr/bin/env python3
"""E2 — verify parse_markdown.py emits a consecutive-anchor WARN for back-to-
back images, AND does NOT emit one for images separated by text.

Positive: tests/sample-consec.md → expect WARN + non-empty collision array
Negative: tests/sample-spaced.md → expect empty collision array + no WARN
"""
from __future__ import annotations
import json, pathlib, subprocess, sys

SCRIPT = pathlib.Path.home() / ".claude/skills/x-article-publisher/scripts/parse_markdown.py"
HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)
# Touch the asset paths so parse_markdown's existence check doesn't error
for f in ("a.jpg", "b.jpg"):
    p = ASSETS / f
    if not p.exists():
        p.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # minimal JPEG-looking header


def run(md: pathlib.Path) -> tuple[int, dict, str]:
    res = subprocess.run(
        ["python3", str(SCRIPT), str(md)],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(res.stdout)
    except Exception:
        data = {}
    return res.returncode, data, res.stderr


def main() -> int:
    pos_rc, pos_data, pos_err = run(HERE / "sample-consec.md")
    neg_rc, neg_data, neg_err = run(HERE / "sample-spaced.md")

    overall = True

    # Positive case: collision array non-empty, stderr mentions consecutive
    pos_collisions = pos_data.get("consecutive_anchor_collision", [])
    has_warn = "consecutive" in pos_err.lower()
    if not pos_collisions:
        print(f"POS FAIL: consecutive_anchor_collision empty; full keys: {list(pos_data.keys())}")
        print(f"  stderr was: {pos_err.strip()}")
        overall = False
    elif not has_warn:
        print(f"POS FAIL: collision detected but no stderr WARN; got: {pos_err.strip()}")
        overall = False
    else:
        print(f"POS PASS: collisions={len(pos_collisions)}, WARN on stderr")

    # Negative case: collision array empty, no WARN
    neg_collisions = neg_data.get("consecutive_anchor_collision", [])
    if neg_collisions:
        print(f"NEG FAIL: spaced sample triggered collisions: {neg_collisions}")
        overall = False
    elif "consecutive" in neg_err.lower():
        print(f"NEG FAIL: spaced sample WARN-ed on stderr: {neg_err.strip()}")
        overall = False
    else:
        print("NEG PASS: spaced sample = no collision, no WARN")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
