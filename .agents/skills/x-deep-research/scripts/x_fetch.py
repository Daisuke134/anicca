#!/usr/bin/env python3
"""Fetch one X post or X Article through a pinned x-tweet-fetcher revision."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
import sys
from typing import Any

UPSTREAM = (
    "git+https://github.com/ythx-101/x-tweet-fetcher.git"
    "@085b931f53557da9e25c0d2e6aa5b3b980513125"
)
CANONICAL_URL_RE = re.compile(r"^https://x\.com/[^/?#]+/status/\d+$")


def validate_url(url: str) -> str:
    canonical = url.split("?", 1)[0].rstrip("/")
    if not CANONICAL_URL_RE.fullmatch(canonical):
        raise ValueError("expected a canonical X status URL")
    return canonical


def build_command(url: str) -> list[str]:
    return ["uvx", "--from", UPSTREAM, "xtf", "--url", validate_url(url)]


def normalize_payload(url: str, raw: dict[str, Any]) -> dict[str, Any]:
    canonical = validate_url(url)
    tweet = raw.get("tweet")
    kind = "post"
    complete = False
    error_code: str | None = None
    if not isinstance(tweet, dict):
        error_code = "missing_tweet"
    else:
        article = tweet.get("article")
        is_article = bool(tweet.get("is_article") or isinstance(article, dict))
        if is_article:
            kind = "article"
            full_text = article.get("full_text", "") if isinstance(article, dict) else ""
            complete = bool(str(full_text).strip())
            if not complete:
                error_code = "empty_article_body"
        else:
            complete = bool(str(tweet.get("text", "")).strip())
            if not complete:
                error_code = "empty_post_body"
    return {
        "source": "x-tweet-fetcher/fxtwitter",
        "url": canonical,
        "kind": kind,
        "complete": complete,
        "error_code": error_code,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw": raw,
    }


def failure_payload(url: str, error_code: str, detail: str) -> dict[str, Any]:
    return {
        "source": "x-tweet-fetcher/fxtwitter",
        "url": url,
        "kind": "unknown",
        "complete": False,
        "error_code": error_code,
        "detail": detail,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw": None,
    }


def fetch(url: str, timeout_seconds: int = 60) -> tuple[dict[str, Any], int]:
    canonical = validate_url(url)
    try:
        result = subprocess.run(
            build_command(canonical),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return failure_payload(canonical, "upstream_timeout", "fetch exceeded timeout"), 4
    except OSError as exc:
        return failure_payload(canonical, "upstream_unavailable", str(exc)), 4

    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "upstream failed"
        return failure_payload(canonical, "upstream_failed", detail), 4
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        return failure_payload(canonical, "malformed_upstream_json", "upstream returned invalid JSON"), 4
    payload = normalize_payload(canonical, raw)
    return payload, 0 if payload["complete"] else 4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    if args.timeout < 1:
        print(json.dumps(failure_payload(args.url, "invalid_input", "timeout must be positive")))
        return 2
    try:
        payload, exit_code = fetch(args.url, args.timeout)
    except ValueError as exc:
        print(json.dumps(failure_payload(args.url, "invalid_input", str(exc))))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
