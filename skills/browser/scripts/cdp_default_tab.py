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

    python3 cdp_default_tab.py open <url> --owner gig-pass
    python3 cdp_default_tab.py close <target_id> --owner gig-pass
"""
import argparse
import asyncio
import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

import target_ownership

try:
    import websockets
except ImportError:
    print(json.dumps({"ok": False, "reason": "pip install websockets"}))
    sys.exit(1)


def _cdp_base():
    return os.environ.get("CLOAK_CDP_BASE_URL", "http://127.0.0.1:9222").rstrip("/")


def _browser_ws():
    d = json.loads(
        urllib.request.urlopen(f"{_cdp_base()}/json/version", timeout=8).read()
    )
    return d["webSocketDebuggerUrl"]


def _page_ws(target_id):
    parsed = urlparse(_cdp_base())
    return f"ws://{parsed.netloc}/devtools/page/{target_id}"


async def _call(method, params=None):
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})


def open_tab(url, background=False, owner=None):
    owner = target_ownership.require_owner(owner)
    # No browserContextId => the default (persistent, authenticated) context.
    params = {"url": url}
    if background:
        params["background"] = background
    res = asyncio.run(_call("Target.createTarget", params))
    tid = res["targetId"]
    target_ownership.claim_target(tid, owner)
    return {
        "ok": True,
        "target_id": tid,
        "ws": _page_ws(tid),
        "context": "default",
        "background": background,
        "owner": owner,
    }


async def _serve_hidden_tab(url, owner=None):
    owner = target_ownership.require_owner(owner)
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": url, "hidden": True, "background": True},
        }))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(f"Target.createTarget: {msg['error']}")
                target_id = msg["result"]["targetId"]
                break
        target_ownership.claim_target(target_id, owner)
        print(json.dumps({
            "ok": True,
            "target_id": target_id,
            "ws": _page_ws(target_id),
            "context": "default",
            "hidden": True,
            "owner": owner,
        }), flush=True)
        # CDP hidden targets live only for the session that created them. Keep
        # this browser connection open until the collector closes our stdin.
        try:
            await asyncio.get_running_loop().run_in_executor(
                None, sys.stdin.buffer.read
            )
        finally:
            target_ownership.release_target(target_id, owner)


def close_tab(target_id, owner=None):
    owner = target_ownership.require_owner(owner)
    if not target_ownership.owns_target(target_id, owner):
        actual_owner = target_ownership.owner_for_target(target_id)
        raise PermissionError(
            f"target {target_id} is owned by {actual_owner or 'nobody'}, not {owner}"
        )
    asyncio.run(_call("Target.closeTarget", {"targetId": target_id}))
    target_ownership.release_target(target_id, owner)
    return {"ok": True, "closed": target_id, "owner": owner}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("open", "serve-hidden", "close"))
    parser.add_argument("value", nargs="?")
    parser.add_argument("--owner", default=os.environ.get("CLOAK_BROWSER_OWNER"))
    parser.add_argument("--background", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "open":
            out = open_tab(
                args.value or "about:blank",
                background=args.background,
                owner=args.owner,
            )
        elif args.command == "serve-hidden":
            asyncio.run(
                _serve_hidden_tab(args.value or "about:blank", owner=args.owner)
            )
            sys.exit(0)
        else:
            out = (
                close_tab(args.value, owner=args.owner)
                if args.value
                else {"ok": False, "reason": "close needs a target_id"}
            )
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
