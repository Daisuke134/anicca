#!/usr/bin/env python3
"""
redact.py — PII / secrets filter applied BEFORE any embedding payload leaves
the box.

Reads ruleset from `~/.openclaw/skills/skill-for-you/redact.yaml`
(or wherever `--rules` points). Applies regex substitutions to text and
returns (clean_text, counts_by_kind).

Usage as a library:
    from redact import Redactor
    r = Redactor.from_yaml(path)
    clean, counts = r.redact(text)

Usage as a CLI (used by other scripts and for ad-hoc testing):
    cat input.txt | python3 redact.py [--rules path] [--counts]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_RULES = Path(
    os.environ.get(
        "SKILL_FOR_YOU_REDACT_PATH",
        os.path.expanduser("~/.openclaw/skills/skill-for-you/redact.yaml"),
    )
)


def _load_yaml(path: Path) -> dict:
    """Minimal YAML loader. Tries PyYAML first, falls back to a tiny parser
    sufficient for this file's shape (top-level keys + lists of mappings)."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception:
        # Fallback parser: just enough to read our redact.yaml shape.
        # Recognizes:
        #   key:
        #     - sub_key: value
        #       sub_key2: value
        # Strings can be quoted with single quotes (preferred in our file).
        return _yaml_fallback(text)


def _yaml_fallback(text: str) -> dict:
    out: dict = {}
    cur_top: str | None = None
    cur_list: list | None = None
    cur_item: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Top-level key (no indentation, ends with ':')
        if not line.startswith(" ") and line.endswith(":"):
            cur_top = line[:-1].strip()
            out[cur_top] = []
            cur_list = out[cur_top]
            cur_item = None
            continue
        if not line.startswith(" ") and ":" in line:
            # scalar top-level: "version: 1"
            k, v = line.split(":", 1)
            out[k.strip()] = _parse_scalar(v.strip())
            cur_top = None
            cur_list = None
            continue
        # List item start
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("- "):
            cur_item = {}
            cur_list.append(cur_item)  # type: ignore[union-attr]
            stripped = stripped[2:]
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                cur_item[k.strip()] = _parse_scalar(v.strip())
            elif stripped:
                cur_list[-1] = _parse_scalar(stripped)  # type: ignore[union-attr]
                cur_item = None
            continue
        # continuation line in current item
        if cur_item is not None and ":" in stripped:
            k, v = stripped.split(":", 1)
            cur_item[k.strip()] = _parse_scalar(v.strip())
        elif cur_item is not None and not stripped:
            continue
    return out


def _parse_scalar(v: str):
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


class _Rule:
    __slots__ = ("kind", "regex", "replacement")

    def __init__(self, kind: str, pattern: str, replacement: str):
        self.kind = kind
        self.regex = re.compile(pattern)
        self.replacement = replacement


class Redactor:
    def __init__(self, rules: List[_Rule], skip_globs: List[str]):
        self.rules = rules
        self.skip_globs = skip_globs

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_RULES) -> "Redactor":
        if not path.exists():
            return cls([], [])
        spec = _load_yaml(path) or {}
        rules: List[_Rule] = []
        for group in ("secrets", "env_paths", "pii", "denylist"):
            for entry in spec.get(group) or []:
                if not isinstance(entry, dict):
                    continue
                rules.append(
                    _Rule(
                        kind=str(entry.get("kind", group)),
                        pattern=str(entry["pattern"]),
                        replacement=str(entry.get("replacement", f"<REDACTED:{entry.get('kind', group).upper()}>")),
                    )
                )
        skip = list(spec.get("skip_files") or [])
        return cls(rules, skip)

    def is_skip_path(self, name: str) -> bool:
        from fnmatch import fnmatch

        base = os.path.basename(name)
        return any(fnmatch(base, pat) for pat in self.skip_globs)

    def redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        counts: Dict[str, int] = {}
        out = text
        for rule in self.rules:
            new, n = rule.regex.subn(rule.replacement, out)
            if n:
                counts[rule.kind] = counts.get(rule.kind, 0) + n
                out = new
        return out, counts

    def redact_lines(self, lines: Iterable[str]) -> Tuple[List[str], Dict[str, int]]:
        clean: List[str] = []
        total: Dict[str, int] = {}
        for line in lines:
            cleaned, counts = self.redact(line)
            clean.append(cleaned)
            for k, v in counts.items():
                total[k] = total.get(k, 0) + v
        return clean, total


def main() -> int:
    ap = argparse.ArgumentParser(description="redact.py — PII/secrets filter")
    ap.add_argument("--rules", default=str(DEFAULT_RULES), help="path to redact.yaml")
    ap.add_argument("--counts", action="store_true", help="emit redaction counts on stderr")
    args = ap.parse_args()

    r = Redactor.from_yaml(Path(args.rules))
    text = sys.stdin.read()
    clean, counts = r.redact(text)
    sys.stdout.write(clean)
    if args.counts:
        sys.stderr.write(json.dumps({"redactions_applied": counts}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
