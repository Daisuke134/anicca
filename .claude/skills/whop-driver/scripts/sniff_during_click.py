#!/usr/bin/env -S /Users/anicca/anicca-project/.claude/skills/whop-driver/.venv/bin/python
"""Sniff GraphQL POSTs while clicking iframe campaign cards on Whop.

Flow:
  1. connect_over_cdp + find Whop tab on /discover-campaigns
  2. start request listener (context-scope = sees iframe-internal too)
  3. via raw CDP Input.dispatchMouseEvent: click first Featured card (552, 815)
  4. wait, then click Join Campaign coord (489, 525)
  5. report all GraphQL ops fired

Output:
  JSON {ops: [{op, body, status?, body_preview?}, ...], totalCaptured}
"""
import os, sys, time, json
from patchright.sync_api import sync_playwright

CDP_URL = os.environ.get("CDP_URL", "http://localhost:9222")
TAB_HINT = os.environ.get("TAB_HINT", "discover-campaigns")


def main():
    captured = []
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        ctx = b.contexts[0] if b.contexts else b.new_context()
        page = next((pg for pg in ctx.pages if TAB_HINT in (pg.url or "")), None)
        if not page:
            print(json.dumps({"err": "no whop tab matching " + TAB_HINT})); return

        def on_req(req):
            if req.method == "POST" and "/api/graphql/" in req.url:
                captured.append({
                    "phase": "req",
                    "op": req.url.rsplit("/api/graphql/", 1)[-1].rstrip("/"),
                    "body": (req.post_data or "")[:600],
                })
        def on_res(res):
            if res.request.method == "POST" and "/api/graphql/" in res.url:
                try:
                    body = res.text()[:600]
                except Exception:
                    body = None
                captured.append({
                    "phase": "res",
                    "op": res.url.rsplit("/api/graphql/", 1)[-1].rstrip("/"),
                    "status": res.status,
                    "body_preview": body,
                })
        ctx.on("request", on_req)
        ctx.on("response", on_res)

        # Click Featured Roobet card at coords
        page.mouse.click(552, 815, delay=80)
        time.sleep(4)
        # Click Join Campaign on opened modal
        page.mouse.click(489, 525, delay=80)
        time.sleep(6)

    interesting = [
        c for c in captured
        if c.get("op") not in (
            "coreFetchNotificationBadgesV2", "coreFetchAiChatNotificationBadges",
            "coreFetchUserNotificationPreferences", "coreFetchUserSimpleNotificationPreferences",
            "MessagesFetchDmsChannels", "chatFetchDmChannels",
            "coreFetchPendingAuthorizedUserInviteSummary",
            "GenerateWebsocketJwt", "coreFetchViewerIntercomAccessToken",
        )
    ]
    print(json.dumps({
        "interesting_count": len(interesting),
        "interesting": interesting,
        "total_captured": len(captured),
        "all_ops": sorted({c["op"] for c in captured}),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
