#!/usr/bin/env python3
"""Minimal raw-CDP page driver. Connects to ONE page target by ws url, avoids
Playwright's full-browser attach (which times out on a busy browser).

Stores the active target id in TARGET_FILE so subsequent calls reuse the tab.

Subcommands:
  newtab <url>          open a NEW tab, navigate, set as active target
  use <targetId>        set active target
  nav <url>             navigate active tab
  shot <path>           screenshot active tab
  eval '<js>'           Runtime.evaluate (returnByValue) -> prints JSON result
  find '<text>'         locate first element whose text contains <text>; print center x,y + box
  click <x> <y>         real mouse click at viewport coords
  type '<text>'         insert text into focused element
  press <key>           dispatch a key (e.g. Enter, Tab, Escape, Backspace)
  url                   print active tab url+title
"""
import sys, json, time, urllib.request
from websocket import create_connection

BASE = "http://127.0.0.1:9222"
TARGET_FILE = "/tmp/cdp_target.txt"

def http(path, method="GET"):
    req = urllib.request.Request(BASE + path, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

def list_pages():
    return [t for t in http("/json") if t.get("type") == "page"]

def ws_for(target_id):
    for t in list_pages():
        if t["id"] == target_id:
            return t["webSocketDebuggerUrl"]
    raise SystemExit(f"target {target_id} not found")

class CDP:
    def __init__(self, target_id):
        self.ws = create_connection(ws_for(target_id), timeout=30, max_size=None, suppress_origin=True)
        self._id = 0
    def send(self, method, params=None):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})
    def close(self):
        try: self.ws.close()
        except Exception: pass

def get_target():
    try:
        return open(TARGET_FILE).read().strip()
    except Exception:
        raise SystemExit("no active target; run newtab/use first")

def set_target(tid):
    open(TARGET_FILE, "w").write(tid)

def main():
    cmd = sys.argv[1]
    if cmd == "newtab":
        url = sys.argv[2]
        t = http("/json/new?" + urllib.parse.quote(url, safe=":/?=&%"), method="PUT")
        set_target(t["id"])
        time.sleep(2.0)
        print("TARGET", t["id"])
        return
    if cmd == "use":
        set_target(sys.argv[2]); print("TARGET", sys.argv[2]); return

    tid = get_target()
    c = CDP(tid)
    try:
        c.send("Page.enable")
        c.send("Runtime.enable")
        if cmd == "nav":
            c.send("Page.navigate", {"url": sys.argv[2]})
            time.sleep(3.0)
            print("OK nav")
        elif cmd == "url":
            r = c.send("Runtime.evaluate", {"expression": "JSON.stringify({u:location.href,t:document.title})", "returnByValue": True})
            print(r["result"]["value"])
        elif cmd == "shot":
            r = c.send("Page.captureScreenshot", {"format": "png"})
            import base64
            open(sys.argv[2], "wb").write(base64.b64decode(r["data"]))
            print("SHOT", sys.argv[2])
        elif cmd == "eval":
            r = c.send("Runtime.evaluate", {"expression": sys.argv[2], "returnByValue": True, "awaitPromise": True})
            print(json.dumps(r.get("result", {}).get("value")))
        elif cmd == "find":
            text = sys.argv[2].replace("\\", "\\\\").replace("`", "\\`")
            js = """(() => {
              const want = `%s`.toLowerCase();
              const els = [...document.querySelectorAll('button,a,input,textarea,div,span,label,[role=button],[contenteditable]')];
              for (const el of els) {
                const t = (el.innerText||el.value||el.getAttribute('placeholder')||el.getAttribute('aria-label')||'').trim().toLowerCase();
                if (t && t.includes(want)) {
                  const r = el.getBoundingClientRect();
                  if (r.width>0 && r.height>0) return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),w:Math.round(r.width),h:Math.round(r.height),tag:el.tagName,txt:(el.innerText||el.value||'').slice(0,40)});
                }
              }
              return 'null';
            })()""" % text
            r = c.send("Runtime.evaluate", {"expression": js, "returnByValue": True})
            print(r["result"]["value"])
        elif cmd == "click":
            x, y = float(sys.argv[2]), float(sys.argv[3])
            for ev in ("mousePressed", "mouseReleased"):
                c.send("Input.dispatchMouseEvent", {"type": ev, "x": x, "y": y, "button": "left", "clickCount": 1})
            time.sleep(0.4)
            print("OK click", x, y)
        elif cmd == "type":
            c.send("Input.insertText", {"text": sys.argv[2]})
            print("OK type")
        elif cmd == "keys":
            # send each char as a real keyDown/keyUp (works on input[type=time]/number)
            for ch in sys.argv[2]:
                vk = ord(ch.upper()) if ch.isalnum() else 0
                c.send("Input.dispatchKeyEvent", {"type": "keyDown", "text": ch, "key": ch, "windowsVirtualKeyCode": vk})
                c.send("Input.dispatchKeyEvent", {"type": "keyUp", "text": ch, "key": ch, "windowsVirtualKeyCode": vk})
                time.sleep(0.12)
            print("OK keys")
        elif cmd == "press":
            keymap = {"Enter": ("Enter", 13), "Tab": ("Tab", 9), "Escape": ("Escape", 27), "Backspace": ("Backspace", 8)}
            k, code = keymap.get(sys.argv[2], (sys.argv[2], 0))
            c.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": k, "windowsVirtualKeyCode": code})
            c.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": k, "windowsVirtualKeyCode": code})
            print("OK press", k)
        else:
            print("unknown cmd", cmd)
    finally:
        c.close()

import urllib.parse
if __name__ == "__main__":
    main()
