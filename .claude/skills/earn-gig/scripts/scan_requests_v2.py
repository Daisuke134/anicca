"""
Better /requests scan: get full body once, split by ブックマーク, map IDs in DOM order.
"""
import asyncio, json, re
import websockets, urllib.request

def find_tab():
    with urllib.request.urlopen("http://localhost:9222/json", timeout=30) as r:
        targets = json.loads(r.read())
    for t in targets:
        if t.get("type")=="page" and "coconala.com" in t.get("url",""):
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
    print(f"tab: {ws_url}")
    async with websockets.connect(ws_url, max_size=30*1024*1024) as ws:
        cdp=CDP(ws); rt=asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            await cdp.send("Page.navigate", {"url":"https://coconala.com/requests"})
            await asyncio.sleep(15)
            # Get full body + ordered IDs (= DOM order from /requests/{id} anchors)
            body = (await cdp.send("Runtime.evaluate",{"expression":"document.body.innerText","returnByValue":True}))["result"]["value"]
            ids_js = r"""
            (function(){
              const ids=[]; const seen=new Set();
              document.querySelectorAll('a[href*="/requests/"]').forEach(a => {
                const m=(a.getAttribute('href')||'').match(/\/requests\/(\d+)/);
                if (!m) return;
                if (seen.has(m[1])) return; seen.add(m[1]);
                ids.push(m[1]);
              });
              return ids;
            })()
            """
            ids = (await cdp.send("Runtime.evaluate",{"expression": ids_js,"returnByValue":True}))["result"]["value"]
            print(f"ids: {len(ids)}, body: {len(body)} chars")

            # Split by ブックマーク (each chunk = 1 card content)
            chunks = body.split("ブックマーク")
            print(f"chunks: {len(chunks)} (= expected {len(ids)+1} including header/footer)")

            # Map chunk[i] → ids[i] (= approximate, may be off by 1)
            cards = []
            for i, c in enumerate(chunks[:len(ids)]):
                if len(c.strip()) < 100: continue
                # Extract stats from chunk
                ym = re.search(r'予算\s*\n([^\n]+(?:\n[^\n]+)?)', c)
                om = re.search(r'応募者数\s*([0-9]+)', c)
                dm = re.search(r'あと\s*([0-9]+)\s*日', c)
                ended = '本日終了' in c or '募集を終了' in c or '募集終了' in c
                # category + title = first 2 non-empty lines
                lines = [l.strip() for l in c.split("\n") if l.strip()]
                cat = lines[-3] if len(lines)>=3 else "?"
                title = lines[-2] if len(lines)>=2 else "?"
                cards.append({
                    "id": ids[i] if i < len(ids) else "?",
                    "cat": cat[:30],
                    "title": title[:80],
                    "yosan": (ym.group(1).replace("\n"," ").strip() if ym else "?")[:25],
                    "oubo": int(om.group(1)) if om else None,
                    "ato": int(dm.group(1)) if dm else None,
                    "ended": ended,
                })
            alive = [c for c in cards if not c["ended"] and c["oubo"] is not None]
            alive.sort(key=lambda c: (c["oubo"], -(c["ato"] or 0)))
            print(f"\nalive (sorted by 応募↑): {len(alive)}")
            for c in alive[:35]:
                print(f"  /req/{c['id']:8} 応募{c['oubo']:3} あと{c['ato']:2}日 ¥{c['yosan']:18} | {c['cat'][:15]:15} | {c['title'][:60]}")
            # save
            import os
            out = "/Users/anicca/.claude/skills/earn-gig/state/requests_scan.json"
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out,"w") as f: json.dump({"alive":alive,"all":cards}, f, ensure_ascii=False, indent=2)
            print(f"\nsaved: {out}")
        finally:
            rt.cancel()
            try: await rt
            except: pass
asyncio.run(main())
