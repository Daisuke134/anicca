#!/usr/bin/env python3
"""Minimal raw-CDP driver for the running CloakBrowser daily-driver (CDP :9222).

Why raw CDP (not playwright connect_over_cdp): with ~40 tabs open, playwright's
browser-level auto-attach takes ~56s every connect. Raw per-page CDP attaches in
~100ms, lets us do ONE discrete step per call, screenshot, and let Dais tap a
CAPTCHA between calls. We ONLY ever touch a tab we created — never Dais's tabs,
never close the browser.

Uses homebrew python3 (has websocket-client). Run with:
  /opt/homebrew/bin/python3 cdp.py <cmd> ...

Commands:
  new [url]               create a new tab, print its targetId
  nav <tid> <url>         navigate tab to url
  shot <tid> <out.png>    screenshot tab to file
  eval <tid> <jsfile>     run JS (file path or '-' for stdin) in tab, print JSON result
  text <tid>              print document.body.innerText (truncated)
  url  <tid>              print current url + title
  close <tid>             close ONLY this tab (must be one we created)
"""
import sys, json, base64, time, os
from websocket import create_connection

# Port is configurable via CDP_PORT env so a SECOND isolated CloakBrowser instance
# (a dedicated clip-account profile on its own port) can be driven without touching
# Dais's daily-driver on :9222. Default stays :9222.
_PORT = os.environ.get("CDP_PORT", "9222")
CDP = f"http://localhost:{_PORT}"
WS_BROWSER = None


def _browser_ws():
    import urllib.request
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


def new_tab(url="about:blank"):
    ws = create_connection(_browser_ws(), timeout=20, suppress_origin=True)
    try:
        r = _rpc(ws, 1, "Target.createTarget", {"url": url})
        return r["targetId"]
    finally:
        ws.close()


def page_ws(tid):
    return f"ws://localhost:{_PORT}/devtools/page/{tid}"


def _connect_page(tid):
    return create_connection(page_ws(tid), timeout=30, max_size=None, suppress_origin=True)


def navigate(tid, url):
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "Page.enable")
        _rpc(ws, 2, "Page.navigate", {"url": url})
        time.sleep(0.5)
    finally:
        ws.close()


def bring_front(tid):
    """Page.bringToFront — make this tab the visible/focused one so IG autoplays reels (warmup)."""
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "Page.enable")
        _rpc(ws, 2, "Page.bringToFront")
        time.sleep(0.3)
    finally:
        ws.close()


def screenshot(tid, out):
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "Page.enable")
        r = _rpc(ws, 2, "Page.captureScreenshot", {"format": "png"})
        with open(out, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return out
    finally:
        ws.close()


def evaluate(tid, expr):
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "Runtime.enable")
        r = _rpc(ws, 2, "Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True,
            "userGesture": True,
        })
        if r.get("exceptionDetails"):
            return {"__error__": str(r["exceptionDetails"].get("text") or r["exceptionDetails"])}
        return r.get("result", {}).get("value")
    finally:
        ws.close()


def _rect_center(tid, selector):
    expr = (
        "(()=>{const el=document.querySelector(%r);if(!el)return null;"
        "el.scrollIntoView({block:'center'});const r=el.getBoundingClientRect();"
        "return {x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()"
        % selector
    )
    return evaluate(tid, expr)


def click_xy(tid, x, y):
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        _rpc(ws, 2, "Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        _rpc(ws, 3, "Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        return {"clicked": [x, y]}
    finally:
        ws.close()


def click_sel(tid, selector):
    c = _rect_center(tid, selector)
    if not c:
        return {"__error__": "no element " + selector}
    return click_xy(tid, c["x"], c["y"])


def insert_text(tid, text):
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "Input.insertText", {"text": text})
        return {"inserted": text}
    finally:
        ws.close()


def press_key(tid, key, code=None, vk=None):
    ws = _connect_page(tid)
    try:
        p = {"type": "keyDown", "key": key}
        if code:
            p["code"] = code
        if vk:
            p["windowsVirtualKeyCode"] = vk
        _rpc(ws, 1, "Input.dispatchKeyEvent", p)
        p2 = dict(p); p2["type"] = "keyUp"
        _rpc(ws, 2, "Input.dispatchKeyEvent", p2)
        return {"key": key}
    finally:
        ws.close()


def set_file(tid, selector, path, index=0):
    """Set a file on an <input type=file> via DOM.setFileInputFiles (no OS dialog)."""
    ws = _connect_page(tid)
    try:
        _rpc(ws, 1, "DOM.enable")
        root = _rpc(ws, 2, "DOM.getDocument", {"depth": -1})["root"]["nodeId"]
        # collect all matching nodeIds
        res = _rpc(ws, 3, "DOM.querySelectorAll", {"nodeId": root, "selector": selector})
        node_ids = res.get("nodeIds", [])
        if not node_ids:
            return {"__error__": "no file input for " + selector}
        nid = node_ids[min(index, len(node_ids) - 1)]
        _rpc(ws, 4, "DOM.setFileInputFiles", {"nodeId": nid, "files": [path]})
        return {"set": path, "node": nid, "of": len(node_ids)}
    finally:
        ws.close()


def get_url(tid):
    return evaluate(tid, "({url:location.href,title:document.title})")


def close_tab(tid):
    ws = create_connection(_browser_ws(), timeout=20, suppress_origin=True)
    try:
        _rpc(ws, 1, "Target.closeTarget", {"targetId": tid})
    finally:
        ws.close()


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == "new":
        print(new_tab(a[1] if len(a) > 1 else "about:blank"))
    elif cmd == "nav":
        navigate(a[1], a[2]); print("OK")
    elif cmd == "front":
        bring_front(a[1]); print("OK")
    elif cmd == "shot":
        print(screenshot(a[1], a[2]))
    elif cmd == "eval":
        src = sys.stdin.read() if a[2] == "-" else open(a[2]).read()
        print(json.dumps(evaluate(a[1], src), ensure_ascii=False))
    elif cmd == "text":
        t = evaluate(a[1], "document.body.innerText")
        print((t or "")[:4000])
    elif cmd == "url":
        print(json.dumps(get_url(a[1]), ensure_ascii=False))
    elif cmd == "clicksel":
        print(json.dumps(click_sel(a[1], a[2]), ensure_ascii=False))
    elif cmd == "clickxy":
        print(json.dumps(click_xy(a[1], int(a[2]), int(a[3])), ensure_ascii=False))
    elif cmd == "insert":
        print(json.dumps(insert_text(a[1], a[2]), ensure_ascii=False))
    elif cmd == "key":
        print(json.dumps(press_key(a[1], a[2]), ensure_ascii=False))
    elif cmd == "setfile":
        idx = int(a[4]) if len(a) > 4 else 0
        print(json.dumps(set_file(a[1], a[2], a[3], idx), ensure_ascii=False))
    elif cmd == "close":
        close_tab(a[1]); print("CLOSED")
    else:
        print("unknown cmd", cmd); sys.exit(1)


if __name__ == "__main__":
    main()
