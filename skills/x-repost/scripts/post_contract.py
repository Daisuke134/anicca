#!/usr/bin/env python3
"""Fail-closed contracts applied after model writing and before publishing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")


def language_matches(language: str, text: str) -> bool:
    has_japanese = bool(JAPANESE.search(text))
    return has_japanese if language == "ja" else (
        language == "en" and not has_japanese and bool(LATIN.search(text))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=("en", "ja"), required=True)
    parser.add_argument("--text-file", type=Path, required=True)
    args = parser.parse_args()
    text = args.text_file.read_text(encoding="utf-8").strip()
    matched = bool(text) and language_matches(args.language, text)
    print(json.dumps({"language": args.language, "matched": matched}, sort_keys=True))
    return 0 if matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
