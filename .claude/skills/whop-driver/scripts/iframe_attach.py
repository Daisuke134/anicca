#!/usr/bin/env -S /Users/anicca/.claude/skills/whop-driver/.venv/bin/python
"""whop-driver iframe attach + GraphQL sniff (Phase 1: one-shot harvest).

Connects to CloakBrowser daily-driver (:9222) via patchright connect_over_cdp,
finds the existing Whop tab (must be logged in already), navigates to the
discover-campaigns sub-app, and captures every request the iframe fires —
both to whop.com/api/graphql/* and *.apps.whop.com.

Output:
  ~/.smtm/earn-loops/whop/sniff/discover-<UTC>.jsonl   (one request per line)

Use the captured (URL, headers, post_data) to build server-side curl replays
and graduate to a cookie-only daemon.

NOTE: stays in lean mode — single navigation, ~20s capture window, writes
raw requests only. Body normalization / op-name extraction is done in a
follow-up step (sniff_normalize.py) so this script never blocks the daily
loop with parsing logic.
"""
import json, os, sys, time, datetime, pathlib

from patchright.sync_api import sync_playwright

CDP_URL = os.environ.get("CDP_URL", "http://localhost:9222")
TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://whop.com/joined/contentrewards/discover-campaigns-B5C5S1vijHGVt9/app/",
)
INTEREST_HOSTS = ("apps.whop.com", "/api/graphql/")
WAIT_SECONDS = int(os.environ.get("WAIT_SECONDS", "20"))

OUT_DIR = pathlib.Path.home() / ".smtm" / "earn-loops" / "whop" / "sniff"
OUT_DIR.mkdir(parents=True, exist_ok=True)
stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
out_path = OUT_DIR / f"discover-{stamp}.jsonl"


def matches(url: str) -> bool:
    return any(h in url for h in INTEREST_HOSTS)


def main():
    captured = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        # CloakBrowser exposes existing contexts; pick the default
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()

        # Find a page already on whop.com (= our logged-in tab) or open one
        page = None
        for pg in ctx.pages:
            if "whop.com" in (pg.url or ""):
                page = pg
                break
        if page is None:
            page = ctx.new_page()

        def on_request(req):
            if not matches(req.url):
                return
            try:
                post = req.post_data
            except Exception:
                post = None
            captured.append({
                "ts": time.time(),
                "phase": "request",
                "method": req.method,
                "url": req.url,
                "resource_type": req.resource_type,
                "headers": dict(req.headers),
                "post_data": post,
            })

        def on_response(resp):
            if not matches(resp.url):
                return
            try:
                body_preview = resp.text()[:4000]
            except Exception:
                body_preview = None
            captured.append({
                "ts": time.time(),
                "phase": "response",
                "status": resp.status,
                "url": resp.url,
                "headers": dict(resp.headers),
                "body_preview": body_preview,
            })

        # Listen at CONTEXT scope so cross-origin iframes (apps.whop.com) are covered.
        ctx.on("request", on_request)
        ctx.on("response", on_response)

        # Navigate (or stay if already there) + give the iframe time
        print(f"[iframe_attach] nav -> {TARGET_URL}", file=sys.stderr)
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        print(f"[iframe_attach] capturing for {WAIT_SECONDS}s ...", file=sys.stderr)
        time.sleep(WAIT_SECONDS)

        # Enumerate frame URLs so we can see what loaded
        frames = [{"url": f.url, "name": f.name} for f in page.frames]
        print(f"[iframe_attach] frames at end: {json.dumps(frames)}", file=sys.stderr)

        browser.close()

    with out_path.open("w") as f:
        for row in captured:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Print summary to stdout (= machine-parseable for the daily loop)
    summary = {
        "out": str(out_path),
        "captured_count": len(captured),
        "graphql_ops": sorted({
            r["url"].rsplit("/api/graphql/", 1)[-1].rstrip("/")
            for r in captured
            if r.get("phase") == "request" and "/api/graphql/" in r["url"]
        }),
        "apps_whop_urls": sorted({
            r["url"]
            for r in captured
            if r.get("phase") == "request" and "apps.whop.com" in r["url"]
        })[:20],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
