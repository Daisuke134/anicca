#!/usr/bin/env python3
"""Open a tab in the browser's PERSISTENT DEFAULT context (the daily-driver's own session).

Why this exists: cdp_context_lease.py gives each loop an incognito BrowserContext so loops stop
navigating each other's tabs. That isolation is right for most work, but an incognito context only
carries whatever cookies the vault seeds into it — and Coconala's provider/seller area
(coconala.com/mypage/services_lists, /services/add, service edit) rejects a cookie-only seeded
context with a 302 to /login, because it checks auth the base cookie snapshot does not carry. The
persistent default context (where the real logged-in daily-driver session lives) passes that check.

So: B0 storefront work drives the DEFAULT context via this helper; B1/B2 keep using the gig lease.
A tab created with Target.createTarget and NO browserContextId lands in the default context (same
primitive session_vault.py keepalive already uses to reach the authenticated session).

    python3 cdp_default_tab.py open <url>        # -> {"ok":true,"target_id":...,"ws":...}
    python3 cdp_default_tab.py close <target_id> # close a tab THIS helper opened (self-cleanup)
"""
import asyncio
import json
import os
import sys
import urllib.request

CDP = "http://127.0.0.1:9222"

try:
    import websockets
except ImportError:
    print(json.dumps({"ok": False, "reason": "pip install websockets"}))
    sys.exit(1)


def _browser_ws():
    d = json.loads(urllib.request.urlopen(f"{CDP}/json/version", timeout=8).read())
    return d["webSocketDebuggerUrl"]


async def _call(method, params=None):
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})


def open_tab(url, background=False):
    # No browserContextId => the default (persistent, authenticated) context.
    params = {"url": url}
    if background:
        params["background"] = background
    res = asyncio.run(_call("Target.createTarget", params))
    tid = res["targetId"]
    return {
        "ok": True,
        "target_id": tid,
        "ws": f"ws://127.0.0.1:9222/devtools/page/{tid}",
        "context": "default",
        "background": background,
    }


def close_tab(target_id):
    asyncio.run(_call("Target.closeTarget", {"targetId": target_id}))
    return {"ok": True, "closed": target_id}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "open"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if cmd == "open":
            out = open_tab(arg or "about:blank", background="--background" in sys.argv)
        elif cmd == "close":
            out = close_tab(arg) if arg else {"ok": False, "reason": "close needs a target_id"}
        else:
            out = {"ok": False, "reason": f"unknown command {cmd}"}
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
