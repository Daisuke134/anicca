"""
Click 応募する with Network domain enabled — capture POST + response to understand why no-nav.
"""
import asyncio, json, base64, sys
import websockets

class CDP:
    def __init__(self,ws): self.ws=ws; self.next_id=0; self.pending={}; self.events=[]
    async def reader(self):
        while True:
            try: raw=await self.ws.recv()
            except: return
            try: d=json.loads(raw)
            except: continue
            mid=d.get("id")
            if mid and mid in self.pending:
                f=self.pending.pop(mid)
                if not f.done():
                    if "error" in d: f.set_exception(RuntimeError(d['error']))
                    else: f.set_result(d.get("result",{}))
            else:
                # event
                m = d.get("method")
                if m and m.startswith(("Network.","Page.frame")):
                    self.events.append(d)
    async def send(self, m, p=None, t=30):
        self.next_id+=1; mid=self.next_id
        f=asyncio.get_event_loop().create_future(); self.pending[mid]=f
        msg={"id":mid,"method":m}
        if p: msg["params"]=p
        await self.ws.send(json.dumps(msg))
        try: return await asyncio.wait_for(f, timeout=t)
        except asyncio.TimeoutError: self.pending.pop(mid,None); raise

async def main():
    import urllib.request
    with urllib.request.urlopen("http://localhost:9222/json", timeout=30) as r:
        targets = json.loads(r.read())
    ws_url = None
    for t in targets:
        if t.get("type") == "page" and "coconala.com" in t.get("url",""):
            ws_url = t.get("webSocketDebuggerUrl"); break
    if not ws_url:
        for t in targets:
            if t.get("type") == "page":
                ws_url = t.get("webSocketDebuggerUrl"); break
    print(f"ws: {ws_url}")

    async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
        cdp=CDP(ws); rt=asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable")
            await cdp.send("Runtime.enable")
            await cdp.send("Network.enable")
            # Nav
            await cdp.send("Page.navigate", {"url":"https://coconala.com/requests/5121769"})
            await asyncio.sleep(7)
            # clear events accumulated during nav
            cdp.events.clear()
            print(f"events cleared before click")

            # Click via Input.dispatchMouseEvent at button center
            js_loc = r"""
            (function(){
              const btns = document.querySelectorAll('button');
              for (const b of btns) {
                if ((b.innerText||'').trim() === '応募する' && !b.disabled) {
                  b.scrollIntoView({block:'center'});
                  const r = b.getBoundingClientRect();
                  return {x: r.x + r.width/2, y: r.y + r.height/2};
                }
              }
              return null;
            })()
            """
            loc = (await cdp.send("Runtime.evaluate", {"expression": js_loc, "returnByValue": True}))["result"]["value"]
            print(f"button at: {loc}")
            await asyncio.sleep(1)
            x, y = int(loc["x"]), int(loc["y"])
            await cdp.send("Input.dispatchMouseEvent", {"type":"mousePressed", "x":x, "y":y, "button":"left", "clickCount":1})
            await cdp.send("Input.dispatchMouseEvent", {"type":"mouseReleased", "x":x, "y":y, "button":"left", "clickCount":1})
            print("click sent")
            # Wait for events to accumulate
            await asyncio.sleep(6)

            # Inspect captured events
            print(f"\n=== {len(cdp.events)} events captured ===")
            requests = [e for e in cdp.events if e.get("method") == "Network.requestWillBeSent"]
            responses = [e for e in cdp.events if e.get("method") == "Network.responseReceived"]
            failures = [e for e in cdp.events if e.get("method") == "Network.loadingFailed"]
            print(f"  requests: {len(requests)}, responses: {len(responses)}, failures: {len(failures)}")
            # show requests + statuses
            req_map = {}
            for r in requests:
                p = r["params"]
                req_map[p["requestId"]] = {"url": p["request"]["url"], "method": p["request"]["method"]}
            for r in responses:
                p = r["params"]
                rid = p["requestId"]
                if rid in req_map:
                    req_map[rid]["status"] = p["response"]["status"]
                    req_map[rid]["mime"] = p["response"]["mimeType"]
            # show ones that look meaningful (= POST / non-image)
            for rid, info in req_map.items():
                url = info["url"]
                if any(k in url for k in [".png", ".jpg", ".gif", ".svg", ".woff", ".css", ".js"]) and info.get("method") != "POST":
                    continue
                print(f"  [{info.get('status','?'):>3}] {info['method']:5} {url[:120]}")

            # Look for any error toasts / modals
            js_check = r"""
            (function(){
              const out = {};
              // any alert/notification element
              const alerts = document.querySelectorAll('[role=alert], .toast, .notification, .error-message, .v-snack, .alert');
              out.alerts = Array.from(alerts).map(a => ({text: (a.innerText||'').slice(0,150), visible: a.offsetParent!==null}));
              // is there a modal NOW?
              const dialogs = document.querySelectorAll('[role=dialog], .modal');
              out.dialogs = Array.from(dialogs).map(d => ({text: (d.innerText||'').slice(0,200), visible: d.offsetParent!==null}));
              return out;
            })()
            """
            r = (await cdp.send("Runtime.evaluate", {"expression": js_check, "returnByValue": True}))["result"]["value"]
            print(f"\n=== alerts: {r.get('alerts')}")
            print(f"=== dialogs: {r.get('dialogs')}")
        finally:
            rt.cancel()
            try: await rt
            except: pass

asyncio.run(main())
