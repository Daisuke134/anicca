# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.40"]
# ///
"""Read-only X search through an already-authenticated CDP browser.

The adapter never navigates X composer, Article editor, settings, messages, or
intent pages. It reuses a dedicated search page, then an about:blank page, and
only then creates a new page.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Any, Sequence

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

PROTECTED_MARKERS = (
    "/compose",
    "/articles/edit",
    "/intent/",
    "/settings",
    "/messages",
)
STATUS_URL_RE = re.compile(r"^https://x\.com/[^/]+/status/\d+")


def classify_page(url: str) -> str:
    if any(marker in url for marker in PROTECTED_MARKERS):
        return "protected"
    if url.startswith("https://x.com/search"):
        return "search"
    if url == "about:blank":
        return "blank"
    return "other"


def choose_search_page(pages: Sequence[Any]) -> Any | None:
    for kind in ("search", "blank"):
        for page in pages:
            if classify_page(page.url) == kind:
                return page
    return None


def canonical_status_url(url: str) -> str:
    match = STATUS_URL_RE.match(url.split("?", 1)[0])
    return match.group(0) if match else ""


def dedupe_results(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        url = canonical_status_url(str(row.get("url", "")))
        if url and url not in unique:
            unique[url] = {**row, "url": url}
    return list(unique.values())


def stop_reason(
    *,
    result_count: int,
    requested_count: int,
    scrolls: int,
    max_scrolls: int,
    stagnant: int,
) -> str | None:
    if result_count >= requested_count:
        return None
    if stagnant >= 3:
        return "stagnant_after_3_scrolls"
    if scrolls >= max_scrolls:
        return "max_scrolls_reached"
    return "insufficient_results"


def _first_status_url(article: Any) -> str:
    for link in article.locator('a[href*="/status/"]').all():
        href = link.get_attribute("href") or ""
        absolute = f"https://x.com{href}" if href.startswith("/") else href
        canonical = canonical_status_url(absolute)
        if canonical:
            return canonical
    return ""


def _label(article: Any, testid: str) -> str:
    locator = article.locator(f'[data-testid="{testid}"]').first
    if locator.count() == 0:
        return ""
    return locator.get_attribute("aria-label") or locator.inner_text().strip()


def extract_visible_results(page: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for article in page.locator('article[data-testid="tweet"]').all():
        url = _first_status_url(article)
        if not url:
            continue
        author = article.locator('div[data-testid="User-Name"]').first
        text = article.locator('div[data-testid="tweetText"]').first
        rows.append(
            {
                "url": url,
                "author": author.inner_text().strip() if author.count() else "",
                "text": text.inner_text().strip() if text.count() else "",
                "metrics": {
                    "reply": _label(article, "reply"),
                    "repost": _label(article, "retweet"),
                    "like": _label(article, "like"),
                    "bookmark": _label(article, "bookmark"),
                },
            }
        )
    return rows


@dataclass
class SearchReport:
    query: str
    mode: str
    requested_count: int
    scrolls: int
    results: list[dict[str, Any]]
    partial_reason: str | None
    page_reused: bool
    page_created: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode,
            "requested_count": self.requested_count,
            "result_count": len(self.results),
            "scrolls": self.scrolls,
            "complete": self.partial_reason is None,
            "partial_reason": self.partial_reason,
            "page_reused": self.page_reused,
            "page_created": self.page_created,
            "results": self.results,
        }


def _error(code: str, detail: str, exit_code: int) -> int:
    print(json.dumps({"complete": False, "error_code": code, "detail": detail}))
    return exit_code


def search_x(
    *,
    query: str,
    mode: str,
    count: int,
    max_scrolls: int,
    cdp_url: str,
) -> SearchReport:
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        if not browser.contexts:
            raise RuntimeError("authenticated_context_missing")
        context = browser.contexts[0]
        pages = context.pages
        protected = [(page, page.url) for page in pages if classify_page(page.url) == "protected"]
        target = choose_search_page(pages)
        page_reused = target is not None
        page_created = False
        if target is None:
            target = context.new_page()
            page_created = True

        encoded = urllib.parse.quote(query)
        suffix = "&f=live" if mode == "live" else ""
        target.goto(
            f"https://x.com/search?q={encoded}&src=typed_query{suffix}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        if "/i/flow/login" in target.url:
            raise RuntimeError("authenticated_context_missing")

        article_locator = target.locator('article[data-testid="tweet"]')
        no_results = target.get_by_text("No results for", exact=False)
        try:
            article_locator.first.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError:
            if no_results.count():
                return SearchReport(
                    query=query,
                    mode=mode,
                    requested_count=count,
                    scrolls=0,
                    results=[],
                    partial_reason="no_results",
                    page_reused=page_reused,
                    page_created=page_created,
                )
            raise RuntimeError("dom_contract_changed")

        collected: list[dict[str, Any]] = []
        scrolls = 0
        stagnant = 0
        previous_unique = 0
        while True:
            collected = dedupe_results([*collected, *extract_visible_results(target)])
            if len(collected) >= count or scrolls >= max_scrolls or stagnant >= 3:
                break
            visible_before = article_locator.count()
            target.mouse.wheel(0, 1_600)
            scrolls += 1
            try:
                target.wait_for_function(
                    """before => document.querySelectorAll(
                        'article[data-testid="tweet"]'
                    ).length !== before""",
                    arg=visible_before,
                    timeout=2_500,
                )
            except PlaywrightTimeoutError:
                pass
            if len(collected) == previous_unique:
                stagnant += 1
            else:
                stagnant = 0
            previous_unique = len(collected)

        collected = dedupe_results([*collected, *extract_visible_results(target)])
        for page, original_url in protected:
            if page.url != original_url:
                raise RuntimeError("protected_page_changed")

        reason = stop_reason(
            result_count=len(collected),
            requested_count=count,
            scrolls=scrolls,
            max_scrolls=max_scrolls,
            stagnant=stagnant,
        )
        return SearchReport(
            query=query,
            mode=mode,
            requested_count=count,
            scrolls=scrolls,
            results=collected[:count],
            partial_reason=reason,
            page_reused=page_reused,
            page_created=page_created,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--mode", choices=("live", "top"), default="top")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--max-scrolls", type=int, default=30)
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    args = parser.parse_args()
    if args.count < 1 or args.max_scrolls < 0:
        return _error("invalid_input", "count must be positive and max-scrolls non-negative", 2)
    try:
        report = search_x(
            query=args.query,
            mode=args.mode,
            count=args.count,
            max_scrolls=args.max_scrolls,
            cdp_url=args.cdp_url,
        )
    except RuntimeError as exc:
        code = str(exc)
        exit_code = 3 if code in {"dom_contract_changed", "protected_page_changed"} else 2
        return _error(code, code.replace("_", " "), exit_code)
    except (PlaywrightError, OSError) as exc:
        return _error("browser_unavailable", str(exc), 2)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
