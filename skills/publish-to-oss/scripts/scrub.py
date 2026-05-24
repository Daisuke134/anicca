#!/usr/bin/env python3
"""scrub.py — data-driven personal-value remover for the OSS publish pipeline.

Walks a STAGED copy of the repo and replaces every occurrence of the owner's
real personal values with placeholders. The values are NOT hardcoded here —
they are read from identity/profile.json ({{profile.lateness.stakeholders.senderType}}Name, {{profile.lateness.stakeholders.channel}}s, phone, address,
lat/lon, advisor {{profile.lateness.stakeholders.channel}}, …) plus a small static list of infra/handle patterns
that don't live in profile.json (Tailscale IPs, social handles, school
usernames, repo owner handle).

Why data-driven: blacklist whack-a-mole misses things (proved 3× on 2026-05-24).
Reading the actual personal values from profile.json means we scrub the real
strings wherever they appear, in any file, automatically.

Usage:
  scrub.py <{{profile.lateness.stakeholders.senderType}}d_dir>            # scrub in place, print report
  scrub.py <{{profile.lateness.stakeholders.senderType}}d_dir> --check    # report only, exit 1 if anything WOULD change
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
PROFILE = ANICCA_HOME / "identity" / "profile.json"

# Static regex patterns NOT in profile.json → placeholder.
# These contain the owner's REAL values (handles, school, IPs), so they live in a
# GITIGNORED file ($ANICCA_HOME/identity/scrub-patterns.json) — NOT hardcoded here,
# otherwise this very script would leak them when published. Falls back to an
# empty set if the file is absent (profile-driven scrub still runs).
def _load_static() -> dict:
    f = ANICCA_HOME / "identity" / "scrub-patterns.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}

STATIC = _load_static()

# profile leaves we deliberately do NOT scrub (too generic / would over-match)
SKIP_KEYS = {"identity.timezone", "identity.languages", "channels.reportPlatform",
             "work.schedule", "alarm.wakeTime", "lateness.defaultSenderType"}

TEXT_EXT = {".md", ".sh", ".py", ".js", ".ts", ".mjs", ".json", ".txt", ".yaml",
            ".yml", ".html", ".css", ".swift", ".plist", ".toml", ".env", ".example"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache"}


def _leaves(o, prefix=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(o, list):
        for v in o:
            yield from _leaves(v, prefix)
    elif isinstance(o, str):
        yield prefix, o


def build_map() -> list[tuple[str, str]]:
    """Return (pattern_or_literal, replacement) pairs, longest-literal first."""
    pairs: list[tuple[str, str, bool]] = []  # (needle, repl, is_regex)
    if PROFILE.exists():
        prof = json.loads(PROFILE.read_text())
        for key, val in _leaves(prof):
            if key in SKIP_KEYS:
                continue
            v = val.strip()
            # only scrub specific-enough values (avoid nuking common words)
            if len(v) >= 5 and not v.isdigit():
                placeholder = "{{profile." + key + "}}"
                pairs.append((v, placeholder, False))
    # sort literals longest-first so substrings don't pre-empt
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    out = [(p[0], p[1], p[2]) for p in pairs]
    out += [(pat, repl, True) for pat, repl in STATIC.items()]
    return out


def scrub_text(text: str, mapping) -> tuple[str, int]:
    n = 0
    for needle, repl, is_regex in mapping:
        if is_regex:
            text, c = re.subn(needle, repl, text)
        else:
            c = text.count(needle)
            if c:
                text = text.replace(needle, repl)
        n += c
    return text, n


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: scrub.py <{{profile.lateness.stakeholders.senderType}}d_dir> [--check]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    check = "--check" in sys.argv
    mapping = build_map()
    print(f"scrub map: {len(mapping)} rules (profile + static)")
    total, touched = 0, 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in TEXT_EXT and ".example" not in p.name:
            continue
        try:
            orig = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        new, n = scrub_text(orig, mapping)
        if n:
            total += n
            touched += 1
            print(f"  {n:3d} × {p.relative_to(root)}")
            if not check:
                p.write_text(new, encoding="utf-8")
    print(f"\n{'WOULD SCRUB' if check else 'SCRUBBED'} {total} occurrences in {touched} files")
    if check and total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
