#!/usr/bin/env python3
"""Turn public search-result HTML into bounded Chinese-source candidates."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ALLOWED_DOMAINS = (
    "xiaohongshu.com",
    "douyin.com",
    "kuaishou.com",
    "bilibili.com",
    "weibo.com",
    "tieba.baidu.com",
    "zhihu.com",
)


def canonical_domain(hostname: str | None) -> str | None:
    host = (hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    for domain in ALLOWED_DOMAINS:
        if host == domain or host.endswith(f".{domain}"):
            return domain
    return None


def result_url(href: str) -> str | None:
    candidate = f"https:{href}" if href.startswith("//") else href
    parsed = urlparse(candidate)
    if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
        values = parse_qs(parsed.query).get("uddg") or []
        candidate = unquote(values[0]) if values else ""
        parsed = urlparse(candidate)
    if parsed.scheme != "https" or not canonical_domain(parsed.hostname):
        return None
    return candidate


class ResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self.capture: str | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            url = result_url(values.get("href") or "")
            if url:
                self.rows.append({"url": url, "title": "", "snippet": ""})
                self.capture, self.buffer = "title", []
        elif "result__snippet" in classes and self.rows:
            self.capture, self.buffer = "snippet", []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.capture or not self.rows:
            return
        if (self.capture == "title" and tag == "a") or self.capture == "snippet":
            self.rows[-1][self.capture] = " ".join("".join(self.buffer).split())
            self.capture, self.buffer = None, []


def collect(search_html: str, query: str, observed_at: str, limit: int = 21) -> dict:
    parser = ResultParser()
    parser.feed(search_html)
    candidates, seen = [], set()
    for row in parser.rows:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        domain = canonical_domain(urlparse(row["url"]).hostname)
        if not domain:
            continue
        candidates.append({
            **row,
            "query": query,
            "source_domain": domain,
            "source_language": "zh",
        })
        if len(candidates) >= limit:
            break
    return {
        "schema_version": 1,
        "receipt_type": "CHINESE_PUBLIC_SOURCE_CANDIDATES",
        "query": query,
        "observed_at": observed_at,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-file", type=Path, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--limit", type=int, default=21)
    args = parser.parse_args()
    print(json.dumps(collect(
        args.html_file.read_text(encoding="utf-8", errors="replace"),
        args.query,
        args.observed_at,
        max(1, args.limit),
    ), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
