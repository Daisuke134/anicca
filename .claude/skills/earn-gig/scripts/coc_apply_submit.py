"""
On /requests/{id}/apply form: snapshot + fill 3 fields + 確認画面 + 個人情報同意 + 応募する FINAL.
"""
import asyncio, json, base64, sys
import websockets, urllib.request

def find_apply_tab(req_id):
    with urllib.request.urlopen("http://localhost:9222/json", timeout=30) as r:
        targets = json.loads(r.read())
    for t in targets:
        if t.get("type")=="page" and f"/requests/{req_id}/apply" in t.get("url",""):
            return t.get("webSocketDebuggerUrl")
    return None

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
    proposal_file = sys.argv[2] if len(sys.argv) > 2 else "/Users/anicca/.claude/skills/earn-gig/artifacts/5121769/proposal_v2.md"
    price = sys.argv[3] if len(sys.argv) > 3 else "5000"
    deadline = sys.argv[4] if len(sys.argv) > 4 else "2026-07-03"

    with open(proposal_file) as f: proposal_text = f.read()
    print(f"proposal: {len(proposal_text)} chars, price={price}, deadline={deadline}")

    ws_url = find_apply_tab(req_id)
    if not ws_url:
        print(f"NO TAB on /requests/{req_id}/apply"); return
    print(f"tab: {ws_url}")

    OUT = "/private/tmp/claude-501/-Users-anicca-anicca-project/0020a17d-3b66-42e6-ad2e-2f7d506ea2c4/scratchpad"

    async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
        cdp = CDP(ws); rt = asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            # Verify on /apply page
            url = (await cdp.send("Runtime.evaluate", {"expression":"location.href","returnByValue":True}))["result"]["value"]
            print(f"on: {url}")
            if "/apply" not in url:
                print("Not on /apply page; nav-ing");
                await cdp.send("Page.navigate", {"url":f"https://coconala.com/requests/{req_id}/apply"})
                await asyncio.sleep(10)

            # Inspect form fields
            js_inspect = r"""
            (function(){
              const out = {};
              out.textareas = Array.from(document.querySelectorAll('textarea')).map(el => ({
                ph: el.placeholder, name: el.name, id: el.id, max: el.maxLength, vis: el.offsetParent!==null
              }));
              out.inputs = Array.from(document.querySelectorAll('input:not([type=hidden])')).map(el => ({
                type: el.type, name: el.name, id: el.id, ph: el.placeholder, vis: el.offsetParent!==null
              }));
              out.buttons = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent!==null).map(b => ({
                text: (b.innerText||'').trim().slice(0,40), type: b.type, disabled: b.disabled
              }));
              return out;
            })()
            """
            r = (await cdp.send("Runtime.evaluate", {"expression": js_inspect, "returnByValue": True}))["result"]["value"]
            print(f"\n=== form ===")
            print(f"textareas: {len(r.get('textareas',[]))}")
            for ta in r.get('textareas',[])[:5]: print(f"  {ta}")
            print(f"inputs: {len(r.get('inputs',[]))}")
            for inp in r.get('inputs',[])[:10]: print(f"  {inp}")
            print(f"buttons: {len(r.get('buttons',[]))}")
            for btn in r.get('buttons',[])[:15]: print(f"  {btn}")

            # screenshot for review
            shot = await cdp.send("Page.captureScreenshot", {"format":"png"})
            with open(f"{OUT}/apply_form_initial.png","wb") as f: f.write(base64.b64decode(shot["data"]))
            print(f"\nscreenshot saved: {OUT}/apply_form_initial.png")
        finally:
            rt.cancel()
            try: await rt
            except: pass

asyncio.run(main())
