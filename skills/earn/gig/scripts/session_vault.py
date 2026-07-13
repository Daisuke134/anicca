#!/usr/bin/env python3
"""Keep the logins alive across crashes so no human ever has to re-authenticate.

Cookies live inside the Chromium profile, and a hard kill (OOM, crash, an unlucky cleanup) can take
recent ones with it. Losing them means re-login, and re-login means 2FA, and 2FA means a human —
which is exactly the thing the loops must never need.

So: snapshot every cookie the browser holds into a JSON vault on a schedule, and restore from the
vault when a session turns out to be gone. Same idea as Playwright's storageState ("produce
authenticated browser state and save it to a file... reuse this state and start already
authenticated"), done over CDP against the running daily-driver.

    python3 session_vault.py dump      # snapshot every cookie -> auth-state.json
    python3 session_vault.py restore   # push the vault back into the live browser
    python3 session_vault.py status    # how many cookies, which origins, how old
"""
import asyncio
import json
import os
import sys
import time
import urllib.request

CDP = "http://127.0.0.1:9222"
VAULT_DIR = os.path.expanduser("~/.cloak/vault/daily-driver")
VAULT = os.path.join(VAULT_DIR, "auth-state.json")
KEEP_BACKUPS = 8

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
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})


def dump():
    res = asyncio.run(_call("Storage.getCookies"))
    cookies = res.get("cookies", [])
    if not cookies:
        # never overwrite a good vault with an empty snapshot from a half-dead browser
        return {"ok": False, "reason": "browser returned zero cookies; vault left untouched"}

    os.makedirs(VAULT_DIR, exist_ok=True)
    if os.path.exists(VAULT):
        os.replace(VAULT, os.path.join(VAULT_DIR, f"auth-state.{int(os.path.getmtime(VAULT))}.json"))
        backups = sorted(f for f in os.listdir(VAULT_DIR) if f.startswith("auth-state.") and f != "auth-state.json")
        for old in backups[:-KEEP_BACKUPS]:
            os.remove(os.path.join(VAULT_DIR, old))

    payload = {"ts": int(time.time()), "cookies": cookies}
    tmp = VAULT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, VAULT)
    os.chmod(VAULT, 0o600)  # cookies are credentials

    domains = sorted({c.get("domain", "") for c in cookies})
    return {"ok": True, "cookies": len(cookies), "domains": len(domains), "vault": VAULT}


def restore():
    if not os.path.exists(VAULT):
        return {"ok": False, "reason": "no vault yet — run dump while logged in"}
    saved = json.load(open(VAULT))
    cookies = saved.get("cookies", [])
    if not cookies:
        return {"ok": False, "reason": "vault is empty"}
    asyncio.run(_call("Storage.setCookies", {"cookies": cookies}))
    return {"ok": True, "restored": len(cookies), "age_hours": round((time.time() - saved.get("ts", 0)) / 3600, 1)}


def status():
    if not os.path.exists(VAULT):
        return {"ok": False, "reason": "no vault yet"}
    saved = json.load(open(VAULT))
    cookies = saved.get("cookies", [])
    interesting = sorted({c["domain"] for c in cookies if any(
        k in c.get("domain", "") for k in ("coconala", "instagram", "youtube", "google", "x.com", "tiktok", "promote"))})
    return {"ok": True, "cookies": len(cookies), "age_hours": round((time.time() - saved.get("ts", 0)) / 3600, 1),
            "logged_in_origins": interesting}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        out = {"dump": dump, "restore": restore, "status": status}[cmd]()
    except KeyError:
        out = {"ok": False, "reason": f"unknown command {cmd}"}
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
