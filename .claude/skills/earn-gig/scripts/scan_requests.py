"""
Scan /requests via Dais's logged-in tab, extract all visible candidates with applicant count + deadline.
"""
import asyncio, json, base64, re
import websockets, urllib.request

def find_tab():
    with urllib.request.urlopen("http://localhost:9222/json", timeout=30) as r:
        targets = json.loads(r.read())
    # prefer existing coconala tab
    for t in targets:
        if t.get("type")=="page" and "coconala.com" in t.get("url","") and "/login" not in t.get("url",""):
            return t.get("webSocketDebuggerUrl")
    for t in targets:
        if t.get("type")=="page":
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
    ws_url = find_tab()
    if not ws_url:
        print("no tab"); return
    print(f"tab: {ws_url}")
    async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
        cdp=CDP(ws); rt=asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            await cdp.send("Page.navigate", {"url":"https://coconala.com/requests"})
            await asyncio.sleep(15)  # let JS fully render
            # Extract structured card data
            js = r"""
            (function(){
              // Each card is an <a href="/requests/{id}"> wrapping content
              const cards = [];
              const seen = new Set();
              document.querySelectorAll('a[href*="/requests/"]').forEach(a => {
                const m = (a.getAttribute('href')||'').match(/\/requests\/(\d+)/);
                if (!m) return;
                const id = m[1];
                if (seen.has(id)) return; seen.add(id);
                // climb up to the card container
                let card = a;
                for (let i=0; i<5 && card.parentElement; i++) {
                  card = card.parentElement;
                  if ((card.innerText||'').includes('応募人数') || (card.innerText||'').includes('募集期限')) break;
                }
                const txt = (card.innerText||'').trim();
                const ym = txt.match(/予算\s*([0-9,千万円未満〜~ー\s-]+)/);
                const om = txt.match(/応募人数\s*([0-9]+)/);
                const dm = txt.match(/あと\s*([0-9]+)\s*日/);
                const cat_m = txt.match(/^(?:[^\n]*\n)?([^\n]+)\n/);
                // title is usually the link text or first heading
                const title = (a.innerText||'').trim().split('\n')[0].slice(0,80);
                cards.push({
                  id,
                  title,
                  yosan: ym ? ym[1].replace(/\s+/g,' ').trim() : '?',
                  oubo: om ? parseInt(om[1]) : null,
                  ato: dm ? parseInt(dm[1]) : null,
                  text_snip: txt.slice(0,300).replace(/\n/g,' | '),
                });
              });
              return cards.slice(0, 50);
            })()
            """
            res = (await cdp.send("Runtime.evaluate", {"expression": js, "returnByValue": True}))["result"]["value"]
            print(f"\ncards found: {len(res)}")
            print("\n=== alive candidates (sorted by 応募人数 asc) ===")
            # filter alive + sort
            alive = [c for c in res if c.get("ato") is not None and c.get("oubo") is not None]
            alive.sort(key=lambda c: (c["oubo"], -c["ato"]))
            print(f"alive: {len(alive)}")
            for c in alive[:30]:
                print(f"  [{c['id']}] 応募{c['oubo']:2}人 あと{c['ato']:2}日 ¥={c['yosan'][:18]:18} | {c['text_snip'][:160]}")
            # save to file
            out = "/Users/anicca/.claude/skills/earn-gig/state/requests_scan.json"
            import os; os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out,"w") as f: json.dump({"alive":alive,"all":res}, f, ensure_ascii=False, indent=2)
            print(f"\nsaved: {out}")
        finally:
            rt.cancel()
            try: await rt
            except: pass
asyncio.run(main())
