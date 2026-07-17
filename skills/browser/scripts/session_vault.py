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
    python3 session_vault.py keepalive <url> [url...]   # navigate authed pages to extend server-side session + detect logout
    python3 session_vault.py totp <secret_key_or_@service>  # print a fresh TOTP code so login can finish without a human

Why keepalive: cookie restore only saves a HARD crash. It does NOT save (b) the server invalidating
the session or (c) a 2FA/passkey re-prompt. keepalive hits an authenticated page on a schedule so the
server keeps the session warm, and reports logged_out=true the moment a page redirects to /login — so
a loop can re-auth itself early instead of discovering it mid-task.

Why totp: authenticator-app 2FA is the one re-login path a machine CAN finish alone. Store the TOTP
secret once (issued when 2FA is enabled) and generate the 6-digit code with pyotp — no phone, no human.
Google passkey and Apple-ID-SMS are NOT solvable in-browser; earn accounts must use an AI-owned account
with app-based 2FA, never Dais's passkey-locked Google.
"""
import asyncio
import json
import os
import sys
import time
import urllib.request

CDP_PORT = os.environ.get("SESSION_VAULT_PORT", "9222")
CDP = f"http://127.0.0.1:{CDP_PORT}"
VAULT_DIR = os.path.expanduser(os.environ.get("SESSION_VAULT_DIR", "~/.cloak/vault/daily-driver"))
VAULT = os.path.join(VAULT_DIR, "auth-state.json")
TOTP_SECRETS = os.path.join(VAULT_DIR, "totp-secrets.json")  # {"@coconala": "BASE32SECRET", ...}, chmod 600
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


# Which origins are worth carrying localStorage for. Cookies cover auth on most sites,
# but some SPAs keep the auth/session token in localStorage — so a hard kill that loses the
# profile also loses login unless we snapshot it too (steel-browser: "cookies AND local
# storage across requests"). Keep this list to the sites the loops actually log into.
LS_ORIGINS = [
    "https://coconala.com", "https://www.instagram.com", "https://www.tiktok.com",
    "https://www.youtube.com", "https://x.com",
]


async def _localstorage(op, data=None):
    """op='read' -> {origin: {k:v}}; op='write' -> push data back. One tab per origin over CDP."""
    out = {}
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        mid = [0]

        async def call(method, params=None, sess=None):
            mid[0] += 1
            i = mid[0]
            m = {"id": i, "method": method, "params": params or {}}
            if sess:
                m["sessionId"] = sess
            await ws.send(json.dumps(m))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == i:
                    if "error" in msg:
                        raise RuntimeError(msg["error"])
                    return msg.get("result", {})

        origins = LS_ORIGINS if op == "read" else list((data or {}).keys())
        for origin in origins:
            try:
                t = await call("Target.createTarget", {"url": origin})
                tid = t["targetId"]
                sess = (await call("Target.attachToTarget", {"targetId": tid, "flatten": True}))["sessionId"]
                await asyncio.sleep(2)
                if op == "read":
                    r = await call("Runtime.evaluate",
                                   {"expression": "JSON.stringify(Object.fromEntries(Object.entries(localStorage)))",
                                    "returnByValue": True}, sess=sess)
                    val = r.get("result", {}).get("value")
                    if val and val != "{}":
                        out[origin] = json.loads(val)
                else:
                    kv = data.get(origin, {})
                    expr = "".join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in kv.items())
                    if expr:
                        await call("Runtime.evaluate", {"expression": expr}, sess=sess)
                await call("Target.closeTarget", {"targetId": tid})
            except Exception:
                continue  # one bad origin must not abort the whole snapshot
    return out


def dump():
    res = asyncio.run(_call("Storage.getCookies"))
    cookies = res.get("cookies", [])
    if not cookies:
        # never overwrite a good vault with an empty snapshot from a half-dead browser
        return {"ok": False, "reason": "browser returned zero cookies; vault left untouched"}

    try:
        local_storage = asyncio.run(_localstorage("read"))
    except Exception:
        local_storage = {}

    os.makedirs(VAULT_DIR, exist_ok=True)
    if os.path.exists(VAULT):
        os.replace(VAULT, os.path.join(VAULT_DIR, f"auth-state.{int(os.path.getmtime(VAULT))}.json"))
        backups = sorted(f for f in os.listdir(VAULT_DIR) if f.startswith("auth-state.") and f != "auth-state.json")
        for old in backups[:-KEEP_BACKUPS]:
            os.remove(os.path.join(VAULT_DIR, old))

    payload = {"ts": int(time.time()), "cookies": cookies, "localStorage": local_storage}
    tmp = VAULT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, VAULT)
    os.chmod(VAULT, 0o600)  # cookies + tokens are credentials

    domains = sorted({c.get("domain", "") for c in cookies})
    return {"ok": True, "cookies": len(cookies), "domains": len(domains),
            "localStorage_origins": len(local_storage), "vault": VAULT}


def restore():
    if not os.path.exists(VAULT):
        return {"ok": False, "reason": "no vault yet — run dump while logged in"}
    saved = json.load(open(VAULT))
    cookies = saved.get("cookies", [])
    if not cookies:
        return {"ok": False, "reason": "vault is empty"}
    asyncio.run(_call("Storage.setCookies", {"cookies": cookies}))
    ls = saved.get("localStorage", {})
    if ls:
        try:
            asyncio.run(_localstorage("write", ls))
        except Exception:
            pass
    return {"ok": True, "restored": len(cookies), "localStorage_origins": len(ls),
            "age_hours": round((time.time() - saved.get("ts", 0)) / 3600, 1)}


def status():
    if not os.path.exists(VAULT):
        return {"ok": False, "reason": "no vault yet"}
    saved = json.load(open(VAULT))
    cookies = saved.get("cookies", [])
    interesting = sorted({c["domain"] for c in cookies if any(
        k in c.get("domain", "") for k in ("coconala", "instagram", "youtube", "google", "x.com", "tiktok", "promote"))})
    return {"ok": True, "cookies": len(cookies), "age_hours": round((time.time() - saved.get("ts", 0)) / 3600, 1),
            "logged_in_origins": interesting}


def _has_instagram_sessionid(cookies):
    """True if any cookie is a live instagram.com sessionid. Used because IG lets a half-dead
    session (ds_user_id survives, sessionid expired) sit on the feed WITHOUT ever redirecting to
    /login — so URL-redirect detection alone false-negatives logged_out on Instagram."""
    return any(
        c.get("name") == "sessionid" and "instagram.com" in c.get("domain", "")
        for c in cookies
    )


def _logged_out_for(url, final, cookies, page_text=""):
    """Decide logged_out for one keepalive page.

    - URL redirected to /login /signin etc -> logged_out (works for coconala and most sites).
    - instagram.com specifically -> ALSO require a live sessionid cookie, since IG does not
      redirect a half-dead session to /login. OR'd with the redirect check per spec: either
      signal alone is enough to declare logged_out on instagram.com.
    - x.com specifically -> ALSO check the rendered page text for "Something went wrong", the
      generic error X's client renders when a stale/invalidated auth_token cookie is present —
      it does NOT redirect to /login (a hard-crashed React tree just sits on the current URL),
      so URL-redirect detection alone false-negatives here exactly like the Instagram case
      (real incident 2026-07-17: keepalive reported logged_out=false while a live screenshot
      showed "Something went wrong" on x.com/home -- this cost a full manual re-diagnosis).
    - non-instagram/non-x domains: only the redirect check applies.
    """
    redirected = any(k in final.lower() for k in ("/login", "/signin", "/sign_in", "accounts.google.com/signin"))
    if "instagram.com" in url.lower() and not _has_instagram_sessionid(cookies):
        return True
    if "x.com" in url.lower() and "something went wrong" in (page_text or "").lower():
        return True
    return redirected


async def _keepalive(urls):
    """Open each url in its own tab, wait for it to settle, and see where it ended up.
    A redirect to a /login or /signin URL means the server dropped the session. For
    instagram.com pages, also check the live sessionid cookie; for x.com pages, also read the
    rendered page text for a "Something went wrong" crash state (see _logged_out_for) — neither
    site reliably redirects a half-dead session to /login."""
    results = []
    async with websockets.connect(_browser_ws(), max_size=64 * 1024 * 1024) as ws:
        mid = [0]

        async def call(method, params=None, sess=None):
            mid[0] += 1
            i = mid[0]
            m = {"id": i, "method": method, "params": params or {}}
            if sess:
                m["sessionId"] = sess
            await ws.send(json.dumps(m))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == i:
                    if "error" in msg:
                        raise RuntimeError(msg["error"])
                    return msg.get("result", {})

        for url in urls:
            t = await call("Target.createTarget", {"url": url})
            tid = t["targetId"]
            sess = (await call("Target.attachToTarget", {"targetId": tid, "flatten": True}))["sessionId"]
            await asyncio.sleep(4)  # let redirects/JS settle
            hist = await call("Page.getNavigationHistory", sess=sess)
            entries = hist.get("entries", [])
            final = entries[hist.get("currentIndex", len(entries) - 1)]["url"] if entries else url
            cookies = []
            if "instagram.com" in url.lower():
                cookies_res = await call("Storage.getCookies", {})
                cookies = cookies_res.get("cookies", [])
            page_text = ""
            if "x.com" in url.lower():
                r = await call("Runtime.evaluate",
                               {"expression": "document.body ? document.body.innerText : ''",
                                "returnByValue": True}, sess=sess)
                page_text = r.get("result", {}).get("value", "") or ""
            logged_out = _logged_out_for(url, final, cookies, page_text)
            results.append({"url": url, "final": final, "logged_out": logged_out})
            await call("Target.closeTarget", {"targetId": tid})
    return results


def keepalive(urls):
    if not urls:
        return {"ok": False, "reason": "usage: keepalive <url> [url...]"}
    res = asyncio.run(_keepalive(urls))
    any_out = any(r["logged_out"] for r in res)
    return {"ok": not any_out, "logged_out": any_out, "pages": res}


def totp(key):
    """Generate a fresh 6-digit code. key is a base32 secret, or @service to look it up in the vault."""
    try:
        import pyotp
    except ImportError:
        return {"ok": False, "reason": "pip install pyotp"}
    secret = key
    if key.startswith("@"):
        if not os.path.exists(TOTP_SECRETS):
            return {"ok": False, "reason": f"no {TOTP_SECRETS}; store {{\"{key}\": \"BASE32\"}} chmod 600"}
        secret = json.load(open(TOTP_SECRETS)).get(key)
        if not secret:
            return {"ok": False, "reason": f"{key} not in totp-secrets.json"}
    try:
        code = pyotp.TOTP(secret.replace(" ", "")).now()
    except Exception as e:
        return {"ok": False, "reason": f"bad secret: {e}"}
    return {"ok": True, "code": code}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    rest = sys.argv[2:]
    try:
        if cmd == "keepalive":
            out = keepalive(rest)
        elif cmd == "totp":
            out = totp(rest[0]) if rest else {"ok": False, "reason": "usage: totp <secret|@service>"}
        else:
            out = {"dump": dump, "restore": restore, "status": status}[cmd]()
    except KeyError:
        out = {"ok": False, "reason": f"unknown command {cmd}"}
    except Exception as e:
        out = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
