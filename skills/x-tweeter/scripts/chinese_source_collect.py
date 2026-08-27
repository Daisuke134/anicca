#!/usr/bin/env python3
"""Turn public search-result HTML into bounded Chinese-source candidates."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


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


def content_url_allowed(value: str) -> bool:
    parsed = urlparse(value)
    domain = canonical_domain(parsed.hostname)
    host, path = (parsed.hostname or "").lower(), parsed.path
    if domain == "xiaohongshu.com":
        return host in {"xiaohongshu.com", "www.xiaohongshu.com"} and path.startswith("/explore/")
    if domain == "douyin.com":
        return host in {"douyin.com", "www.douyin.com"} and path.startswith("/video/")
    if domain == "kuaishou.com":
        return host in {"kuaishou.com", "www.kuaishou.com"} and path.startswith("/short-video/")
    if domain == "bilibili.com":
        return host in {"bilibili.com", "www.bilibili.com"} and path.startswith("/video/")
    if domain == "weibo.com":
        return host in {"weibo.com", "www.weibo.com"} and len(path.strip("/").split("/")) >= 2
    if domain == "tieba.baidu.com":
        return host == "tieba.baidu.com" and path.startswith("/p/")
    if domain == "zhihu.com":
        return ((host in {"zhihu.com", "www.zhihu.com"} and path.startswith("/question/"))
                or (host == "zhuanlan.zhihu.com" and path.startswith("/p/")))
    return False


def result_url(href: str) -> str | None:
    candidate = html.unescape(f"https:{href}" if href.startswith("//") else href)
    parsed = urlparse(candidate)
    if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
        values = parse_qs(parsed.query).get("uddg") or []
        candidate = unquote(values[0]) if values else ""
        parsed = urlparse(candidate)
    elif parsed.hostname and parsed.hostname.endswith("bing.com"):
        values = parse_qs(parsed.query).get("u") or []
        encoded = values[0][2:] if values and values[0].startswith("a1") else ""
        try:
            candidate = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
        except (ValueError, UnicodeDecodeError):
            candidate = ""
        parsed = urlparse(candidate)
    if parsed.scheme != "https" or not content_url_allowed(candidate):
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


def collect_markdown(markdown: str, query: str, observed_at: str, limit: int = 21) -> dict:
    candidates, seen = [], set()
    for title, href in re.findall(r"^#{2,4}\s+\[([^]]+)\]\((https?://[^)]+)\)", markdown, re.M):
        url = result_url(href)
        if not url or url in seen:
            continue
        seen.add(url)
        domain = canonical_domain(urlparse(url).hostname)
        candidates.append({
            "url": url,
            "title": " ".join(title.split()),
            "snippet": "",
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


def collect_bing(search_html: str, query: str, observed_at: str, limit: int = 21) -> dict:
    candidates, seen = [], set()
    pattern = r'<li[^>]*class="[^"]*b_algo[^"]*".*?<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    for href, raw_title in re.findall(pattern, search_html, re.S | re.I):
        url = result_url(href)
        if not url or url in seen:
            continue
        seen.add(url)
        candidates.append({
            "url": url,
            "title": " ".join(html.unescape(re.sub(r"<[^>]+>", "", raw_title)).split()),
            "snippet": "",
            "query": query,
            "source_domain": canonical_domain(urlparse(url).hostname),
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


def hydrate(receipt: dict, fetcher, limit: int = 7) -> dict:
    hydrated = []
    for row in receipt.get("candidates", [])[:limit]:
        try:
            text = "\n".join(line.rstrip() for line in (fetcher(row["url"]) or "").splitlines()).strip()
        except Exception:
            continue
        if len(" ".join(text.split())) < 16:
            continue
        domain = canonical_domain(urlparse(row["url"]).hostname)
        hydrated.append({
            **row,
            "source_domain": domain,
            "source_language": "zh",
            "handle": domain,
            "text": text[:6000],
            "metrics": {},
        })
        if len(hydrated) >= limit:
            break
    return {
        **receipt,
        "candidate_count": len(hydrated),
        "candidates": hydrated,
    }


def parse_search_specs(value: str) -> list[tuple[str, str]]:
    specs = []
    for raw in value.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        query, separator, search_url = line.partition("\t")
        if not separator or urlparse(search_url).scheme != "https":
            raise ValueError("search spec must be QUERY<TAB>HTTPS_URL")
        specs.append((query.strip(), search_url.strip()))
    return specs


def discover(query_file: Path, observed_at: str, limit: int = 7) -> dict:
    specs = parse_search_specs(query_file.read_text(encoding="utf-8"))
    buckets, seen = [], set()

    def crawl(url: str) -> str:
        try:
            result = subprocess.run(
                ["crwl", "crawl", url, "-o", "markdown-fit"],
                capture_output=True, text=True, timeout=20, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return result.stdout if result.returncode == 0 else ""

    def scrapy_fetch(url: str) -> str:
        try:
            result = subprocess.run(
                ["scrapy", "fetch", url],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return result.stdout if result.returncode == 0 else ""

    for query, search_url in specs:
        bucket = []
        rows = collect_markdown(crawl(search_url), query, observed_at, limit=3)["candidates"]
        if not rows:
            domain = canonical_domain(urlparse(search_url).hostname)
            fallback_url = (
                "https://html.duckduckgo.com/html/?q="
                + quote(f"site:{domain} {query}")
            )
            rows = collect(scrapy_fetch(fallback_url), query, observed_at, limit=3)["candidates"]
        if not rows:
            bing_url = (
                "https://www.bing.com/search?q="
                + quote(f"site:{domain} {query}")
            )
            rows = collect_bing(scrapy_fetch(bing_url), query, observed_at, limit=3)["candidates"]
        for row in rows:
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            bucket.append(row)
        buckets.append(bucket)

    combined = []
    for index in range(3):
        combined.extend(bucket[index] for bucket in buckets if len(bucket) > index)

    return hydrate({
        "schema_version": 1,
        "receipt_type": "CHINESE_PUBLIC_SOURCE_CANDIDATES",
        "query_count": len(specs),
        "queries": [query for query, _ in specs],
        "observed_at": observed_at,
        "candidates": combined,
    }, crawl, limit=limit)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-file", type=Path)
    parser.add_argument("--query")
    parser.add_argument("--query-file", type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--limit", type=int, default=21)
    args = parser.parse_args()
    if args.query_file:
        result = discover(args.query_file, args.observed_at, max(1, args.limit))
    elif args.html_file and args.query:
        result = collect(
            args.html_file.read_text(encoding="utf-8", errors="replace"),
            args.query, args.observed_at, max(1, args.limit),
        )
    else:
        parser.error("provide --query-file or both --html-file and --query")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
