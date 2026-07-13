"""
Full fresh apply flow on tab B4E21A25:
1. Navigate to detail page /requests/{id}
2. Click 応募する via Input.dispatchMouseEvent
3. Wait + check if /apply nav OR form modal
4. Snapshot result
"""
import asyncio, json, base64, sys
import websockets, urllib.request

class CDP:
    def __init__(self,ws): self.ws=ws; self.next_id=0; self.pending={}
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
    async def send(self, m, p=None, t=30):
        self.next_id+=1; mid=self.next_id
        f=asyncio.get_event_loop().create_future(); self.pending[mid]=f
        msg={"id":mid,"method":m}
        if p: msg["params"]=p
        await self.ws.send(json.dumps(msg))
        try: return await asyncio.wait_for(f, timeout=t)
        except asyncio.TimeoutError: self.pending.pop(mid,None); raise

async def main():
    req_id = sys.argv[1] if len(sys.argv) > 1 else "5121769"
    OUT = "/private/tmp/claude-501/-Users-anicca-anicca-project/0020a17d-3b66-42e6-ad2e-2f7d506ea2c4/scratchpad"
    # use B4E21A25 (= was on /apply error page, navigate it back)
    WS = "ws://localhost:9222/devtools/page/B4E21A25FED96777BD82E70E86394F2F"

    async with websockets.connect(WS, max_size=30*1024*1024) as ws:
        cdp=CDP(ws); rt=asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            # navigate to detail page
            await cdp.send("Page.navigate", {"url": f"https://coconala.com/requests/{req_id}"})
            await asyncio.sleep(10)
            url = (await cdp.send("Runtime.evaluate", {"expression":"location.href","returnByValue":True}))["result"]["value"]
            print(f"on detail: {url}")
            # check 応募する btn exists
            js_btn = r"""
            (function(){
              const buttons = document.querySelectorAll('button');
              for (const b of buttons) {
                if ((b.innerText||'').trim() === '応募する' && !b.disabled) {
                  b.scrollIntoView({block:'center', behavior:'instant'});
                  const r = b.getBoundingClientRect();
                  return {found:true, x: r.x + r.width/2, y: r.y + r.height/2, classes: b.className};
                }
              }
              return {found:false};
            })()
            """
            loc = (await cdp.send("Runtime.evaluate", {"expression": js_btn, "returnByValue": True}))["result"]["value"]
            print(f"button: {loc}")
            if not loc.get("found"):
                print("NO 応募する button"); return
            await asyncio.sleep(1)
            x, y = int(loc["x"]), int(loc["y"])
            # Click via CDP-level mouse event
            await cdp.send("Input.dispatchMouseEvent", {"type":"mousePressed", "x":x, "y":y, "button":"left", "clickCount":1})
            await asyncio.sleep(0.1)
            await cdp.send("Input.dispatchMouseEvent", {"type":"mouseReleased", "x":x, "y":y, "button":"left", "clickCount":1})
            print(f"clicked at ({x},{y})")
            await asyncio.sleep(8)
            url2 = (await cdp.send("Runtime.evaluate", {"expression":"location.href","returnByValue":True}))["result"]["value"]
            print(f"after click url: {url2}")
            # check page content
            body = (await cdp.send("Runtime.evaluate", {"expression":"document.body.innerText.slice(0,2000)","returnByValue":True}))["result"]["value"]
            print(f"\n=== body 2000 ===\n{body}")
            # screenshot
            shot = await cdp.send("Page.captureScreenshot", {"format":"png"})
            with open(f"{OUT}/apply_fresh_after.png","wb") as f: f.write(base64.b64decode(shot["data"]))
            print(f"\nscreenshot: {OUT}/apply_fresh_after.png")
        finally:
            rt.cancel()
            try: await rt
            except: pass

asyncio.run(main())
