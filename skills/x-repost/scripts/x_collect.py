# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.40"]
# ///
"""Recon half of the x-repost loop: read X through the leased CDP browser.

Two modes, one script (the DOM handling and the login repair are identical):

  recon      : run every query in config/queries.txt, scrape the live search results,
               emit candidate posts as JSON on stdout.
  engagement : re-open every post this loop already published and refresh its
               like/reply/quote counts in state/posted.jsonl in place.

The CDP base URL is required -- there is no port default on purpose. A port is not an
identity (see ~/.config/ai/registry/browsers.toml); the caller leases the browser through
browser-guard.sh and passes the URL it was handed.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

# X renders one aggregated aria-label per post action bar, e.g.
# "12 replies, 3 reposts, 48 likes, 2 bookmarks, 9012 views".
_METRIC_RE = re.compile(r"([\d,\.]+)\s+(repl|repost|like|bookmark|view)", re.I)
_KEY = {"repl": "replies", "repost": "reposts", "like": "likes",
        "bookmark": "bookmarks", "view": "views"}


def parse_metrics(aria: str) -> dict:
    out = {}
    for raw, word in _METRIC_RE.findall(aria or ""):
        try:
            out[_KEY[word.lower()]] = int(raw.replace(",", "").split(".")[0])
        except ValueError:
            continue
    return out


def ensure_logged_in(page) -> str:
    """Return the logged-in handle, repairing the session from TWITTER_AUTH_TOKEN if needed.

    The dedicated x-repost profile persists cookies, so the repair path only fires when the
    session actually lapsed. Fails closed: an unauthenticated pass must not silently scrape
    the logged-out landing page and call it a result.
    """
    for attempt in (1, 2):
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)
        link = page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
        if link:
            href = link.get_attribute("href") or ""
            return href.strip("/")
        if attempt == 2:
            break
        token = os.environ.get("TWITTER_AUTH_TOKEN", "")
        if not token:
            raise SystemExit("x_collect: not logged in and TWITTER_AUTH_TOKEN is unset")
        page.context.add_cookies([
            {"name": "auth_token", "value": token, "domain": ".x.com", "path": "/",
             "httpOnly": True, "secure": True, "sameSite": "None"},
        ])
    raise SystemExit("x_collect: X session could not be restored from TWITTER_AUTH_TOKEN")


def get_page(browser):
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    for p in ctx.pages:
        if "x.com" in p.url and "doubleclick" not in p.url:
            return p
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def scrape_articles(page, limit: int) -> list:
    rows, seen = [], set()
    for _ in range(6):
        for art in page.query_selector_all('article[data-testid="tweet"]'):
            try:
                link = art.query_selector('a[href*="/status/"]')
                href = link.get_attribute("href") if link else ""
                if not href or "/status/" not in href:
                    continue
                url = "https://x.com" + href.split("/photo/")[0] if href.startswith("/") else href
                if url in seen:
                    continue
                text_el = art.query_selector('div[data-testid="tweetText"]')
                text = text_el.inner_text() if text_el else ""
                if not text.strip():
                    continue
                name_el = art.query_selector('div[data-testid="User-Name"]')
                group = art.query_selector('[role="group"][aria-label]')
                metrics = parse_metrics(group.get_attribute("aria-label") if group else "")
                seen.add(url)
                rows.append({
                    "url": url,
                    "handle": (name_el.inner_text() if name_el else "").replace("\n", " ")[:120],
                    "text": text[:600],
                    "metrics": metrics,
                })
            except Exception:
                continue
        if len(rows) >= limit:
            break
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(1500)
    return rows[:limit]


def recon(page, queries, per_query, exclude_urls, own_handle, time_budget_seconds,
          checkpoint=None):
    out, errors = [], []
    started = time.monotonic()
    attempted = 0
    for index, q in enumerate(queries):
        if index and time.monotonic() - started >= time_budget_seconds:
            errors.extend({"query": pending, "reason": "time_budget_not_attempted"}
                          for pending in queries[index:])
            if checkpoint:
                checkpoint(out, errors, attempted)
            break
        attempted += 1
        url = ("https://x.com/search?q=" + urllib.parse.quote(q)
               + "&src=typed_query&f=live")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4500)
            rows = scrape_articles(page, per_query)
        except Exception as exc:
            errors.append({"query": q, "reason": str(exc)[:200]})
            if checkpoint:
                checkpoint(out, errors, attempted)
            continue
        for row in rows:
            if row["url"] in exclude_urls:
                continue
            if own_handle and f"/{own_handle}/status/" in row["url"]:
                continue
            row["query"] = q
            out.append(row)
        if checkpoint:
            checkpoint(out, errors, attempted)
    # de-dupe across queries, keep the first sighting
    uniq, seen = [], set()
    for row in out:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        uniq.append(row)
    return uniq, errors, attempted


def recon_receipt(handle, queries, rows, errors, attempted, started_at, completed_at=None):
    """Build one mechanical receipt; eligibility remains an owner-model decision."""
    uniq, seen = [], set()
    for row in rows:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        uniq.append(row)
    errors_by_query = {row.get("query"): row.get("reason") for row in errors}
    query_receipts = []
    for index, query in enumerate(queries):
        attempted_query = index < attempted
        reason = errors_by_query.get(query)
        query_receipts.append({
            "query": query,
            "official_search_url": (
                "https://x.com/search?q=" + urllib.parse.quote(query)
                + "&src=typed_query&f=live"
            ),
            "attempted": attempted_query,
            "status": ("not_attempted" if not attempted_query else
                       "error" if reason else "completed"),
            "error": reason,
        })
    return {
        "handle": handle, "query_count": len(queries),
        "started_at": started_at, "completed_at": completed_at,
        "queries_attempted": attempted,
        "queries_not_attempted": len(queries) - attempted,
        "query_receipts": query_receipts,
        "candidate_count": len(uniq), "candidates": uniq,
        "checked_official_urls": sorted({row["url"] for row in uniq}),
        "query_errors": errors,
    }


def write_checkpoint(path: Path, receipt: dict) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, path)


# X leaves a zero-count action out of the action bar's aria-label entirely: a post with no likes
# reads "21 views", not "0 likes, 21 views" (measured 2026-08-19 on two of our own posts). So an
# absent key means zero, and only a missing action bar means unknown. Conflating the two is what
# left 27 of 29 posts recorded as "likes unknown" when they were really zeros.
MEASURED_ACTIONS = ("likes", "replies", "reposts", "bookmarks", "views")

# Sampling cadence by post age. The ranker pays for engagement velocity in the first couple of
# hours, so a single end-state number throws away the signal that decides reach -- but re-reading
# every post every hour would spend minutes of browser time to learn nothing about week-old posts.
SAMPLE_SCHEDULE = (
    (2 * 60, 0),          # under 2h  -> every pass
    (24 * 60, 6 * 60),    # under 24h -> at most every 6h
    (7 * 24 * 60, 24 * 60),  # under 7d -> at most daily
)


def sample_interval_minutes(age_minutes: float):
    for max_age, interval in SAMPLE_SCHEDULE:
        if age_minutes <= max_age:
            return interval
    return None  # older than the window: stop sampling


def read_metrics(page, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    art = page.query_selector('article[data-testid="tweet"]')
    group = art.query_selector('[role="group"][aria-label]') if art else None
    aria = group.get_attribute("aria-label") if group else None
    if not aria:
        return {"ok": False, "reason": "action bar not found"}
    parsed = parse_metrics(aria)
    row = {"ok": True, "aria": aria}
    row.update({k: parsed.get(k, 0) for k in MEASURED_ACTIONS})
    return row


def refresh_engagement(page, posted_path: Path) -> list:
    """Append a timestamped sample per due post, and keep the latest on the posted row."""
    if not posted_path.exists():
        return []
    samples_path = posted_path.with_name("engagement.jsonl")
    now = datetime.now(timezone.utc)

    last_sample = {}
    if samples_path.exists():
        for line in samples_path.read_text(encoding="utf-8").splitlines():
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            at = s.get("sampled_at")
            if s.get("post_url") and at:
                last_sample[s["post_url"]] = max(last_sample.get(s["post_url"], at), at)

    lines = [l for l in posted_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append(None)

    due, updated = [], []
    for rec in records:
        if not rec or not rec.get("post_url"):
            continue
        try:
            posted_at = datetime.fromisoformat(rec["posted_at"])
        except (KeyError, ValueError):
            continue
        age = (now - posted_at.astimezone(timezone.utc)).total_seconds() / 60
        interval = sample_interval_minutes(age)
        if interval is None:
            continue
        prev = last_sample.get(rec["post_url"])
        if prev:
            since = (now - datetime.fromisoformat(prev).astimezone(timezone.utc)).total_seconds() / 60
            if since < interval:
                continue
        due.append((rec, age))

    with samples_path.open("a", encoding="utf-8") as fh:
        for rec, age in due:
            try:
                metrics = read_metrics(page, rec["post_url"])
            except Exception as exc:  # a deleted or unreachable post must not kill the pass
                metrics = {"ok": False, "reason": str(exc)[:200]}
            sample = {"sampled_at": now.isoformat(), "post_url": rec["post_url"],
                      "age_minutes": round(age, 1), **metrics}
            fh.write(json.dumps(sample, ensure_ascii=False) + "\n")
            if metrics.get("ok"):
                rec["engagement"] = {k: metrics[k] for k in MEASURED_ACTIONS}
                updated.append({"post_url": rec["post_url"], "age_minutes": round(age, 1),
                                "engagement": rec["engagement"]})

    with posted_path.open("w", encoding="utf-8") as fh:
        for rec, raw in zip(records, lines):
            fh.write((json.dumps(rec, ensure_ascii=False) if rec is not None else raw) + "\n")
    return updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", required=True, help="leased CDP base URL from browser-guard.sh")
    ap.add_argument("--mode", choices=["recon", "engagement"], default="recon")
    ap.add_argument("--queries", help="queries file (recon mode)")
    ap.add_argument("--per-query", type=int, default=6)
    ap.add_argument("--time-budget-seconds", type=int, default=240)
    ap.add_argument("--output", help="atomically checkpoint recon progress after every query")
    ap.add_argument("--posted", help="state/posted.jsonl")
    args = ap.parse_args()

    posted_path = Path(args.posted).expanduser() if args.posted else None
    already = set()
    if posted_path and posted_path.exists():
        for line in posted_path.read_text(encoding="utf-8").splitlines():
            try:
                already.add(json.loads(line).get("source_url"))
            except json.JSONDecodeError:
                continue

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(args.cdp)
        page = get_page(browser)
        handle = ensure_logged_in(page)
        if args.mode == "engagement":
            result = {"handle": handle,
                      "updated": refresh_engagement(page, posted_path)}
        else:
            queries = [l.strip() for l in Path(args.queries).read_text(encoding="utf-8").splitlines()
                       if l.strip() and not l.strip().startswith("#")]
            started_at = datetime.now(timezone.utc).isoformat()
            checkpoint_path = Path(args.output) if args.output else None
            def checkpoint(rows, errors, attempted):
                if checkpoint_path is not None:
                    write_checkpoint(checkpoint_path, recon_receipt(
                        handle, queries, rows, errors, attempted, started_at,
                    ))
            rows, errors, attempted = recon(
                page, queries, args.per_query, already, handle, max(1, args.time_budget_seconds),
                checkpoint,
            )
            completed_at = datetime.now(timezone.utc).isoformat()
            result = recon_receipt(
                handle, queries, rows, errors, attempted, started_at, completed_at,
            )
            if checkpoint_path is not None:
                write_checkpoint(checkpoint_path, result)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
