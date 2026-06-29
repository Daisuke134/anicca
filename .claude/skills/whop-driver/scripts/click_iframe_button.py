#!/usr/bin/env -S /Users/anicca/anicca-project/.claude/skills/whop-driver/.venv/bin/python
"""Click a button inside Whop's cross-origin iframe via patchright frame_locator.

CDP-attached browser sessions bypass same-origin policy for the agent's
JS access — frame_locator on whop.com sees inside apps.whop.com iframe.

Usage:
  click_iframe_button.py "<button text>"

Default: 'Join Campaign'

Connects to CloakBrowser daily-driver :9222 + finds the active Whop tab.
"""
import os, sys, time, json
from patchright.sync_api import sync_playwright

BUTTON_TEXT = sys.argv[1] if len(sys.argv) > 1 else "Join Campaign"
CDP_URL = os.environ.get("CDP_URL", "http://localhost:9222")
TAB_URL_HINT = os.environ.get("TAB_URL_HINT", "whop.com/joined/contentrewards")


def main():
    captured = []
    result = {"button": BUTTON_TEXT, "clicked": False, "reason": None}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = next((pg for pg in ctx.pages if TAB_URL_HINT in (pg.url or "")), None)
        if page is None:
            result["reason"] = "no matching whop tab"
            print(json.dumps(result)); return

        # Listen for any GraphQL POST so we can prove the click reached the network
        def on_request(req):
            if req.method == "POST" and "/api/graphql/" in req.url:
                captured.append({
                    "op": req.url.rsplit("/api/graphql/", 1)[-1].rstrip("/"),
                    "body": (req.post_data or "")[:300],
                })
        ctx.on("request", on_request)

        # Enumerate frames; find apps.whop.com iframe
        time.sleep(2)
        frames = page.frames
        iframe = next(
            (f for f in frames if "apps.whop.com" in (f.url or "")),
            None,
        )
        if iframe is None:
            # Try via frame_locator on the launch wrapper
            try:
                fl = page.frame_locator('iframe[src*="apps.whop.com"], iframe[src*="core/app/launch"]').first
                fl.get_by_text(BUTTON_TEXT, exact=False).first.click(timeout=8000)
                result["clicked"] = True
                result["reason"] = "frame_locator click"
            except Exception as e:
                result["reason"] = f"no iframe + frame_locator failed: {e}"
        else:
            # Click via the discovered frame directly
            try:
                btn = iframe.get_by_text(BUTTON_TEXT, exact=False).first
                btn.click(timeout=8000)
                result["clicked"] = True
                result["reason"] = f"iframe.get_by_text on {iframe.url[:80]}"
            except Exception as e:
                # Fallback: locator role=button
                try:
                    iframe.get_by_role("button", name=BUTTON_TEXT).first.click(timeout=8000)
                    result["clicked"] = True
                    result["reason"] = "iframe role=button"
                except Exception as e2:
                    result["reason"] = f"both attempts failed: {e} | {e2}"

        time.sleep(4)
        result["captured_after_click"] = captured

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
