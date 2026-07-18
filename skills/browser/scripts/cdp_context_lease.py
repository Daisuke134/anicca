#!/usr/bin/env python3
"""Give each loop its own browser space so they stop destroying each other's work.

Every loop drives the same Chromium. When gig is halfway through a 応募 form and the clip loop
navigates "the" tab, gig's work is gone — and neither loop can tell that it happened.

CDP has the answer already: Target.createBrowserContext is "Similar to an incognito profile but you
can have more than one". So each task leases its own context, and nothing another loop does can reach
into it. Contexts do not share cookies, so the lease seeds the fresh context from the session vault —
the same trick as Playwright's storageState ("reuse this state and start already authenticated").

    python3 cdp_context_lease.py acquire gig            # -> {"context_id":..., "target_id":..., "ws":...}
    python3 cdp_context_lease.py release gig            # dispose the context (tabs die with it)
    python3 cdp_context_lease.py gc --idle-min 45       # reap contexts a crashed loop left behind
    python3 cdp_context_lease.py list
"""
import asyncio
import json
import os
import sys
import time
import urllib.request

CDP = "http://127.0.0.1:9222"
VAULT = os.path.expanduser("~/.cloak/vault/daily-driver/auth-state.json")
LEASES = os.path.expanduser("~/.cloak/vault/leases.json")

try:
    import websockets
except ImportError:
    print(json.dumps({"ok": False, "reason": "pip install websockets"}))
    sys.exit(1)


def _browser_ws():
    d = json.loads(urllib.request.urlopen(f"{CDP}/json/version", timeout=8).read())
    return d["webSocketDebuggerUrl"]


async def _calls(pairs):
    """Run several CDP calls on one browser connection; returns the list of results."""
    out = []
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        for i, (method, params) in enumerate(pairs, start=1):
            await ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == i:
                    if "error" in msg:
                        raise RuntimeError(f"{method}: {msg['error']}")
                    out.append(msg.get("result", {}))
                    break
    return out


def _leases():
    if os.path.exists(LEASES):
        try:
            return json.load(open(LEASES))
        except Exception:
            pass
    return {}


def _save(d):
    os.makedirs(os.path.dirname(LEASES), exist_ok=True)
    tmp = LEASES + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, LEASES)


def acquire(task, url="about:blank", no_seed=False):
    leases = _leases()
    held = leases.get(task)
    if held:  # a task holds at most one context; reuse it rather than piling up
        return {"ok": True, "reused": True, **held}

    cookies = []
    if not no_seed and os.path.exists(VAULT):
        cookies = json.load(open(VAULT)).get("cookies", [])

    (ctx,) = asyncio.run(_calls([("Target.createBrowserContext", {})]))
    ctx_id = ctx["browserContextId"]

    calls = []
    if cookies:
        # a fresh context starts logged out; seed it from the vault
        calls.append(("Storage.setCookies", {"cookies": cookies, "browserContextId": ctx_id}))
    calls.append(("Target.createTarget", {"url": url, "browserContextId": ctx_id}))
    results = asyncio.run(_calls(calls))
    target_id = results[-1]["targetId"]

    lease = {
        "context_id": ctx_id,
        "target_id": target_id,
        "ws": f"ws://127.0.0.1:9222/devtools/page/{target_id}",
        "ts": int(time.time()),
        "cookies_seeded": len(cookies),
    }
    leases[task] = lease
    _save(leases)
    return {"ok": True, "reused": False, **lease}


def release(task):
    leases = _leases()
    held = leases.pop(task, None)
    if not held:
        return {"ok": True, "note": f"{task} held no context"}
    try:
        asyncio.run(_calls([("Target.disposeBrowserContext", {"browserContextId": held["context_id"]})]))
    except Exception as e:
        _save(leases)
        return {"ok": False, "reason": f"dispose failed: {e}", "released_from_ledger": task}
    _save(leases)
    return {"ok": True, "released": task, "context_id": held["context_id"]}


def gc(idle_min=45):
    """A loop killed with -9 never releases. Reap whatever it left holding."""
    leases = _leases()
    now = time.time()
    reaped = []
    for task, held in list(leases.items()):
        if now - held.get("ts", 0) > idle_min * 60:
            try:
                asyncio.run(_calls([("Target.disposeBrowserContext", {"browserContextId": held["context_id"]})]))
            except Exception:
                pass
            leases.pop(task, None)
            reaped.append(task)
    _save(leases)
    return {"ok": True, "reaped": reaped, "still_held": list(leases)}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if cmd == "acquire":
            out = acquire(arg or "unnamed", no_seed="--no-seed" in sys.argv)
        elif cmd == "release":
            out = release(arg or "unnamed")
        elif cmd == "gc":
            idle = int(sys.argv[sys.argv.index("--idle-min") + 1]) if "--idle-min" in sys.argv else 45
            out = gc(idle)
        elif cmd == "list":
            out = {"ok": True, "leases": _leases()}
        else:
            out = {"ok": False, "reason": f"unknown command {cmd}"}
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
