#!/usr/bin/env python3
"""Open a URL in an isolated CDP browser context (= 'incognito-like' cookie jar)
on the running CloakBrowser daily-driver (CDP :9222).

Why: the daily-driver shares cookies across all tabs. If we're already logged
in to a site (e.g. aishigoto.labo on Instagram), navigating to the signup URL
auto-redirects to '/'. Creating a fresh browser context isolates cookies, so
the signup form actually renders.

We persist context IDs in /tmp so we can re-attach to or close them later.

Usage:
  cdp_incognito.py new <url>           create a context + tab; prints CTX_ID TID
  cdp_incognito.py list                list contexts we created
  cdp_incognito.py close <ctx_id>      dispose a context (closes all its tabs)
"""
import sys, json, os, urllib.request
from websocket import create_connection

CDP = "http://localhost:9222"
STATE = "/tmp/cdp_incognito_state.json"


def _browser_ws():
    d = json.load(urllib.request.urlopen(CDP + "/json/version", timeout=5))
    return d["webSocketDebuggerUrl"]


def _rpc(ws, _id, method, params=None):
    ws.send(json.dumps({"id": _id, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


def _load_state():
    if not os.path.exists(STATE):
        return {"contexts": []}
    with open(STATE) as f:
        try:
            return json.load(f)
        except Exception:
            return {"contexts": []}


def _save_state(s):
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2)


def new_context_tab(url):
    ws = create_connection(_browser_ws(), timeout=20, suppress_origin=True)
    try:
        r = _rpc(ws, 1, "Target.createBrowserContext", {"disposeOnDetach": False})
        ctx = r["browserContextId"]
        r = _rpc(ws, 2, "Target.createTarget", {"url": url, "browserContextId": ctx})
        tid = r["targetId"]
        st = _load_state()
        st["contexts"].append({"context_id": ctx, "tid": tid, "url": url})
        _save_state(st)
        return ctx, tid
    finally:
        ws.close()


def list_contexts():
    return _load_state()["contexts"]


def close_context(ctx_id):
    ws = create_connection(_browser_ws(), timeout=20, suppress_origin=True)
    try:
        _rpc(ws, 1, "Target.disposeBrowserContext", {"browserContextId": ctx_id})
    finally:
        ws.close()
    st = _load_state()
    st["contexts"] = [c for c in st["contexts"] if c["context_id"] != ctx_id]
    _save_state(st)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "new":
        url = a[1] if len(a) > 1 else "about:blank"
        ctx, tid = new_context_tab(url)
        print(f"CTX_ID={ctx}")
        print(f"TID={tid}")
    elif cmd == "list":
        for c in list_contexts():
            print(c)
    elif cmd == "close":
        close_context(a[1])
        print("CLOSED")
    else:
        print(f"unknown cmd: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
