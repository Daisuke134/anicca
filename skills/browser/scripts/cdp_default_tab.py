#!/usr/bin/env python3
"""Open a tab in the caller's authenticated leased BrowserContext.

Each loop already supplies a distinct CLOAK_BROWSER_OWNER. cdp_context_lease seeds that owner's
context from the authenticated session vault, so sibling loops can navigate concurrently without
sharing or closing one another's tabs.

    python3 cdp_default_tab.py open <url> --owner gig-pass
    python3 cdp_default_tab.py close <target_id> --owner gig-pass
    python3 cdp_default_tab.py close-owned --owner gig-pass
"""
import argparse
import asyncio
import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

import cdp_context_lease
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


def _lease(owner):
    lease = cdp_context_lease.acquire(owner)
    if not lease.get("ok") or not lease.get("context_id"):
        raise RuntimeError(f"browser context lease failed: {lease.get('reason', 'unknown')}")
    return lease


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
    lease = _lease(owner)
    opened = asyncio.run(_call("Target.createTarget", {
        "url": url,
        "browserContextId": lease["context_id"],
        "background": background,
    }))
    tid = opened["targetId"]
    target_ownership.claim_target(tid, owner)
    return {
        "ok": True,
        "target_id": tid,
        "ws": _page_ws(tid),
        "context": lease["context_id"],
        "background": background,
        "owner": owner,
    }


async def _serve_hidden_tab(url, owner=None):
    owner = target_ownership.require_owner(owner)
    lease = await asyncio.to_thread(_lease, owner)
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": url, "hidden": True, "background": True,
                       "browserContextId": lease["context_id"]},
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
            "context": lease["context_id"],
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
            try:
                await ws.send(json.dumps({
                    "id": 2,
                    "method": "Target.closeTarget",
                    "params": {"targetId": target_id},
                }))
                while True:
                    close = json.loads(await ws.recv())
                    if close.get("id") == 2:
                        if "error" in close:
                            raise RuntimeError(f"Target.closeTarget: {close['error']}")
                        break
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


def close_owned_tabs(owner=None):
    """Reclaim targets left behind when the previous owner process died."""
    owner = target_ownership.require_owner(owner)
    owned = target_ownership.targets_for_owner(owner)
    live = {
        row.get("targetId")
        for row in asyncio.run(_call("Target.getTargets")).get("targetInfos", [])
    }
    closed = []
    pruned = []
    errors = []
    for target_id in sorted(owned):
        if target_id not in live:
            target_ownership.release_target(target_id, owner)
            pruned.append(target_id)
            continue
        try:
            asyncio.run(_call("Target.closeTarget", {"targetId": target_id}))
            target_ownership.release_target(target_id, owner)
            closed.append(target_id)
        except Exception as error:
            errors.append({"target_id": target_id, "reason": str(error)[:160]})
    return {
        "ok": not errors,
        "owner": owner,
        "owned": len(owned),
        "closed": len(closed),
        "pruned": len(pruned),
        "errors": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("open", "serve-hidden", "close", "close-owned"))
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
        elif args.command == "close":
            out = (
                close_tab(args.value, owner=args.owner)
                if args.value
                else {"ok": False, "reason": "close needs a target_id"}
            )
        else:
            out = close_owned_tabs(owner=args.owner)
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
