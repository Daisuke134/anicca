"""Setup mtdc Coconala profile per BP: ひとこと + 自己紹介 + 職業 + 業務領域."""
import asyncio, json, base64
import websockets
WS = "ws://localhost:9222/devtools/page/D9C7CF7E6E521A4690E422E3F1789C0A"
OUT = "/private/tmp/claude-501/-Users-anicca-anicca-project/0020a17d-3b66-42e6-ad2e-2f7d506ea2c4/scratchpad"

PROFILE = {
  "ひとこと": "教育・ビジネス資料を AI 活用で高速制作。継続案件歓迎。",
  "職業": "プロダクトデザイナー／資料制作",
  "自己紹介": (
    "Daisuke と申します。教育コンテンツ・研修資料の PowerPoint 設計と制作、および "
    "その内製化（マスタースライド／テンプレート化）に向けた AI 活用を中心に活動しています。\n\n"
    "慶應義塾大学卒、教育系 SaaS の立ち上げに関わってきた経験から、学習者の視認性と "
    "作り手の編集容易性を両立した資料設計を得意としています。\n\n"
    "・PowerPoint テンプレート（教育向け／企業研修／セミナー資料）\n"
    "・SwiftUI／Python／Web 開発（業務自動化スクリプト）\n"
    "・SNS／TikTok 縦動画の自動生成パイプライン\n\n"
    "AI ツール（Python・LLM 系）を設計補助に用いる場合は、毎案件で開示します。\n"
    "ご相談・見積もりはお気軽にどうぞ。"
  ),
}

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
    async with websockets.connect(WS, max_size=30*1024*1024) as ws:
        cdp=CDP(ws); rt=asyncio.create_task(cdp.reader())
        try:
            await cdp.send("Page.enable"); await cdp.send("Runtime.enable")
            await cdp.send("Page.navigate", {"url":"https://coconala.com/mypage/user"})
            await asyncio.sleep(10)
            # Snapshot all form fields with their labels
            js_snap = r"""
            (function(){
              const fields = [];
              document.querySelectorAll('input:not([type=hidden]), textarea').forEach((el, i) => {
                if (el.offsetParent === null) return;
                // find nearby label
                let label = '';
                const parent = el.closest('div, label, section');
                if (parent) {
                  // look up siblings for label-like text
                  const head = parent.querySelector('label, .label, .heading, h3, h4, .form-label, .form-title');
                  if (head) label = (head.innerText||'').trim().slice(0,40);
                  if (!label) {
                    const all = (parent.innerText||'').trim().split('\n');
                    if (all[0]) label = all[0].trim().slice(0,40);
                  }
                }
                fields.push({
                  i, tag: el.tagName, type: el.type, name: el.name, id: el.id,
                  ph: (el.placeholder||'').slice(0,40),
                  current: (el.value||'').slice(0,60),
                  label,
                });
              });
              return fields.slice(0,40);
            })()
            """
            r = (await cdp.send("Runtime.evaluate", {"expression": js_snap, "returnByValue": True}))["result"]["value"]
            print(f"\n=== form fields on /mypage/user ({len(r)}) ===")
            for f in r:
                print(f"  [{f['i']:2}] {f['tag']:8} type={f['type']:6} ph='{f['ph']:30}' label='{f.get('label','')[:30]:30}' cur='{f.get('current','')[:30]}'")
            shot = await cdp.send("Page.captureScreenshot", {"format":"png", "captureBeyondViewport":True})
            with open(f"{OUT}/profile_form.png","wb") as f2: f2.write(base64.b64decode(shot["data"]))
            print(f"\nfull-page screenshot saved")
        finally:
            rt.cancel()
            try: await rt
            except: pass
asyncio.run(main())
