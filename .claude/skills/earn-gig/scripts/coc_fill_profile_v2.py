"""Update mtdc 自己紹介 + ひとこと: remove 「自動化中心」 framing per adversary fix1."""
import asyncio, json, base64
import websockets
WS = "ws://localhost:9222/devtools/page/D9C7CF7E6E521A4690E422E3F1789C0A"
OUT = "/private/tmp/claude-501/-Users-anicca-anicca-project/0020a17d-3b66-42e6-ad2e-2f7d506ea2c4/scratchpad"

PROFILE = {
  "occupation": "プロダクトデザイナー／資料制作",
  "hito_appeal": "教育・ビジネス資料の設計と制作。シリーズ授業の統一感を重視。",
  "intro": (
    "Daisuke と申します。教育コンテンツ・研修資料の PowerPoint 設計と制作を中心に活動しています。\n\n"
    "慶應義塾大学卒、教育系 SaaS の立ち上げに関わってきた経験から、学習者の視認性と "
    "作り手の編集容易性を両立した資料設計を得意としています。\n\n"
    "得意分野：\n"
    "・PowerPoint テンプレート（教育向け／企業研修／セミナー資料）\n"
    "・マスタースライド設計（次回以降の編集を 5 分で済ませる構成）\n"
    "・配色・タイポグラフィの体系化\n\n"
    "対応スピード：平日 9:00〜23:00 ／ 土日 10:00〜18:00。リアルタイム返信を心がけています。\n"
    "ご相談・お見積もりはお気軽にどうぞ。"
  ),
  "schedule": "平日 9:00〜23:00 / 土日 10:00〜18:00 対応可。リアルタイム返信を心がけています。",
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
            # Click 編集 buttons next to each section first (= UI re-enters edit mode)
            js_open_edit = r"""
            (function(){
              const opened = [];
              document.querySelectorAll('button, [role=button]').forEach(b => {
                const aria = b.getAttribute('aria-label') || '';
                const html = b.outerHTML;
                if (aria.includes('編集') || html.includes('pencil') || html.includes('edit')) {
                  if (b.offsetParent !== null) {
                    b.click();
                    opened.push(aria || html.slice(0,60));
                  }
                }
              });
              return opened;
            })()
            """
            r0 = (await cdp.send("Runtime.evaluate", {"expression": js_open_edit, "returnByValue": True}))["result"]["value"]
            print(f"opened edit modes: {len(r0)}")
            await asyncio.sleep(3)

            js_fill = r"""
            (function(){
              const profile = """ + json.dumps(PROFILE, ensure_ascii=False) + r""";
              function setVal(el, val) {
                const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                setter.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
              }
              const filled = [];
              document.querySelectorAll('input, textarea').forEach((el) => {
                if (el.offsetParent === null) return;
                const ph = el.placeholder || '';
                if (ph.includes('広告クリエイター')) { setVal(el, profile.occupation); filled.push('occupation'); }
                else if (ph.includes('企業様の思いを伝える') || ph.includes('ひとこと')) { setVal(el, profile.hito_appeal); filled.push('hito_appeal'); }
                else if (ph.includes('ロゴデザインを10年') || ph.includes('自己紹介')) { setVal(el, profile.intro); filled.push('intro'); }
              });
              return filled;
            })()
            """
            r = (await cdp.send("Runtime.evaluate", {"expression": js_fill, "returnByValue": True}))["result"]["value"]
            print(f"filled: {r}")
            await asyncio.sleep(2)

            # Click 保存する
            js_save = r"""
            (function(){
              const clicked = [];
              document.querySelectorAll('button').forEach(b => {
                if ((b.innerText||'').trim() === '保存する' && !b.disabled && b.offsetParent !== null) {
                  b.click(); clicked.push(true);
                }
              });
              return clicked.length;
            })()
            """
            r2 = (await cdp.send("Runtime.evaluate", {"expression": js_save, "returnByValue": True}))["result"]["value"]
            print(f"save clicked: {r2}")
            await asyncio.sleep(5)
            shot = await cdp.send("Page.captureScreenshot", {"format":"png", "captureBeyondViewport":True})
            with open(f"{OUT}/profile_v2_saved.png","wb") as f: f.write(base64.b64decode(shot["data"]))
            print(f"screenshot saved")
        finally:
            rt.cancel()
            try: await rt
            except: pass
asyncio.run(main())
