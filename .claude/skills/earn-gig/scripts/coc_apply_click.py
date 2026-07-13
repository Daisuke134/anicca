"""
Click 応募する on /requests/{id} via Input.dispatchMouseEvent (coordinate click).
Vue's .click() may not dispatch handler → use real mouse event at screen coords.
"""
import asyncio, json, base64, sys
import websockets

def get_args():
    if len(sys.argv) < 2:
        print("usage: coc_apply_click.py <request_id> [tab_ws_url]"); sys.exit(1)
    req_id = sys.argv[1]
    ws = sys.argv[2] if len(sys.argv) > 2 else None
    return req_id, ws

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
    req_id, ws_override = get_args()
    # Discover tab if not provided
    if not ws_override:
        import urllib.request
        with urllib.request.urlopen("http://localhost:9222/json", timeout=30) as r:
            targets = json.loads(r.read())
        # use any coconala page tab
        ws_url = None
        for t in targets:
            if t.get("type") == "page" and "coconala.com" in t.get("url",""):
                ws_url = t.get("webSocketDebuggerUrl"); break
        if not ws_url:
            for t in targets:
                if t.get("type") == "page":
                    ws_url = t.get("webSocketDebuggerUrl"); break
        if not ws_url:
            print("no usable tab"); return
    else:
        ws_url = ws_override
    print(f"ws: {ws_url}")

    async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
        cdp=CDP(ws); rt=asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            # Navigate
            await cdp.send("Page.navigate", {"url": f"https://coconala.com/requests/{req_id}"})
            await asyncio.sleep(8)

            # Find 応募する button screen-coords + scroll into view
            js_locate = r"""
            (function(){
              const btns = document.querySelectorAll('button');
              for (const b of btns) {
                if ((b.innerText||'').trim() === '応募する' && !b.disabled) {
                  b.scrollIntoView({block:'center', behavior:'instant'});
                  const r = b.getBoundingClientRect();
                  return {found:true, x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height};
                }
              }
              return {found:false};
            })()
            """
            loc = (await cdp.send("Runtime.evaluate", {"expression": js_locate, "returnByValue": True}))["result"]["value"]
            print(f"button locate: {loc}")
            if not loc.get("found"):
                print("BUTTON NOT FOUND"); return
            await asyncio.sleep(1)

            # Method 1: dispatchEvent (= proper synthetic MouseEvent)
            js_dispatch = r"""
            (function(){
              const btns = document.querySelectorAll('button');
              for (const b of btns) {
                if ((b.innerText||'').trim() === '応募する' && !b.disabled) {
                  ['mousedown','mouseup','click'].forEach(t => {
                    b.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, view:window, button:0}));
                  });
                  return 'dispatched';
                }
              }
              return 'NOT_FOUND';
            })()
            """
            r = await cdp.send("Runtime.evaluate", {"expression": js_dispatch, "returnByValue": True})
            print(f"dispatch: {r.get('result',{}).get('value')}")
            await asyncio.sleep(5)
            url = (await cdp.send("Runtime.evaluate", {"expression":"location.href","returnByValue":True}))["result"]["value"]
            print(f"after dispatch url: {url}")

            # Method 2: Input.dispatchMouseEvent (= CDP-level mouse event at coord)
            x, y = int(loc["x"]), int(loc["y"])
            print(f"\nMethod 2: Input.dispatchMouseEvent at ({x},{y})")
            await cdp.send("Input.dispatchMouseEvent", {"type":"mousePressed", "x":x, "y":y, "button":"left", "clickCount":1})
            await cdp.send("Input.dispatchMouseEvent", {"type":"mouseReleased", "x":x, "y":y, "button":"left", "clickCount":1})
            await asyncio.sleep(6)
            url2 = (await cdp.send("Runtime.evaluate", {"expression":"location.href","returnByValue":True}))["result"]["value"]
            print(f"after Input.click url: {url2}")

            # Check for proposal form on page
            js_form_check = r"""
            (function(){
              const ts = document.querySelectorAll('textarea');
              const ins = document.querySelectorAll('input:not([type=hidden])');
              const out = {
                textareas: Array.from(ts).map(el => ({ph: el.placeholder, vis: el.offsetParent!==null, max: el.maxLength})),
                inputs: Array.from(ins).map(el => ({type: el.type, name: el.name, ph: el.placeholder, vis: el.offsetParent!==null})),
                has_kakunin_btn: !!Array.from(document.querySelectorAll('button')).find(b => (b.innerText||'').includes('確認画面に進む')),
                has_chosen_amount: !!document.body.innerText.includes('提案額'),
                body_tail: document.body.innerText.slice(-600),
              };
              return out;
            })()
            """
            fc = (await cdp.send("Runtime.evaluate", {"expression": js_form_check, "returnByValue": True}))["result"]["value"]
            print(f"\n=== form check ===")
            print(f"  textareas: {fc.get('textareas')}")
            print(f"  inputs(non-hidden) count: {len(fc.get('inputs',[]))}")
            print(f"  has 確認画面に進む btn: {fc.get('has_kakunin_btn')}")
            print(f"  has 提案額 text: {fc.get('has_chosen_amount')}")
            print(f"  body tail: {fc.get('body_tail','')[:400]}")

            # screenshot
            shot = await cdp.send("Page.captureScreenshot", {"format":"png"})
            out = "/private/tmp/claude-501/-Users-anicca-anicca-project/0020a17d-3b66-42e6-ad2e-2f7d506ea2c4/scratchpad"
            with open(f"{out}/click_5121769_after.png","wb") as f: f.write(base64.b64decode(shot["data"]))
            print(f"\nscreenshot saved")
        finally:
            rt.cancel()
            try: await rt
            except: pass

asyncio.run(main())
