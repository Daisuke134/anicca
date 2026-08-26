#!/usr/bin/env python3
"""Fail-closed contracts applied after model writing and before publishing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
KANA = re.compile(r"[\u3040-\u30ff]")
LATIN = re.compile(r"[A-Za-z]")
ENGLISH_PHRASE = re.compile(
    r"\b[A-Za-z][A-Za-z0-9+#./-]*(?:\s+[A-Za-z][A-Za-z0-9+#./-]*){2,}\b"
)


def language_matches(language: str, text: str) -> bool:
    japanese_count = len(JAPANESE.findall(text))
    latin_count = len(LATIN.findall(text))
    # Product names such as AI, X, and SaaS are fine inside Japanese prose. A complete English
    # sentence is not: requiring at least as many Japanese as Latin letters keeps those terms
    # usable while failing closed on the mixed-language model failure seen in production review.
    without_urls = re.sub(r"https?://\S+", "", text)
    japanese_dominant = (
        bool(KANA.search(text))
        and japanese_count >= max(2, latin_count)
        and not ENGLISH_PHRASE.search(without_urls)
    )
    return japanese_dominant if language == "ja" else (
        language == "en" and japanese_count == 0 and latin_count > 0
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
