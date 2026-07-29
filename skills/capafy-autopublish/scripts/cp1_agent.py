#!/usr/bin/env python3
"""
cp1_agent.py — THIN, DUMB browser primitives for Capafy CP1 (Agent Card save).

This is the DETERMINISTIC TOOL half of a two-layer agentic loop. It does NOT
decide anything — it just performs one primitive action against the running
CloakBrowser daily-driver (CDP :9222) and dumps a screenshot + a compact state
readout. The JUDGMENT half is the AGENT (the running LLM) who LOOKS at the
screenshot, decides the next click/type, and calls this tool again — looping
until the real success signal ("カードを保存しました" toast / card-done URL /
server isConfirmedSkills=1) appears.

WHY it exists: the old drive_cp1.py hardcoded DOM-coordinate/text heuristics that
silently broke whenever Capafy changed its publish UI. Per Anthropic "effective
context engineering" (no brittle if-else hardcoded logic — give the model the
data + tools + let it decide), the fix is agentic, not more coordinate tuning.

Every command reconnects over CDP (stateless between calls); the Capafy tab stays
open in the browser across calls, so the agent can act incrementally.

Commands (all print a state readout; most also save a screenshot):
  open <url>                 goto url (reuse capafy tab if present, else new tab)
  shot                       screenshot + dump interactive elements
  state                      dump interactive elements only (no screenshot)
  click <x> <y>              mouse click at viewport coords, then shot
  clicktext "<text>" [nth]   click element whose trimmed text == text (nth, 0-based), then shot
  fill <idx> "<value>"       fill the idx-th field (from `state` field list) via Playwright .fill()
  typeinto <idx> "<text>"    click field idx then type char-by-char (RHF-safe), then shot
  press <key>                press a key on the active element (e.g. Enter)
  upload <idx> <path>        set_input_files on the idx-th file input
  scroll <y>                 window.scrollTo(0, y), then shot
  toast                      report whether success toast / card-done url is present

Screenshot is saved to $CP1_SHOT (default /tmp/cp1_shot.png), viewport-relative
so the (x,y) in the state readout map directly to `click <x> <y>`.
"""
import json, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright

SHOT = os.environ.get("CP1_SHOT", "/tmp/cp1_shot.png")


def _detect_cdp():
    """The daily-driver's CDP port drifts (observed 9222 -> 9223 when 9222 is
    already held by an unrelated local Chrome instance) — auto-detect instead
    of trusting a hardcoded port (self-fix-capafy-loop, 2026-07-21)."""
    override = os.environ.get("CP1_CDP_URL")
    if override:
        return override
    for port in (9222, 9223):
        url = f"http://localhost:{port}"
        try:
            with urllib.request.urlopen(f"{url}/json/version", timeout=2) as r:
                if r.status == 200:
                    return url
        except Exception:
            continue
    return "http://localhost:9222"  # fall back to the documented default


CDP = _detect_cdp()

# JS that returns a compact, bounded list of interactive elements with
# viewport-center coords, so the agent can both SEE (screenshot) and target
# precisely (coords). Fields (inputs/textareas/selects) are listed first with a
# stable index the agent references for fill/typeinto/upload.
STATE_JS = r"""
() => {
  const vis = (e) => {
    const r = e.getBoundingClientRect();
    const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'
      && r.bottom > 0 && r.top < innerHeight + 400;
  };
  const ctr = (e) => { const r = e.getBoundingClientRect();
    return { x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2) }; };
  const short = (t) => (t || '').replace(/\s+/g, ' ').trim().slice(0, 60);

  const fields = [];
  [...document.querySelectorAll('input, textarea, select')].forEach((e) => {
    if (!vis(e) && e.type !== 'file') return;
    const c = ctr(e);
    fields.push({
      i: fields.length, tag: e.tagName.toLowerCase(),
      type: e.type || '', ph: short(e.placeholder), name: e.name || '',
      val: short(e.value || (e.selectedOptions ? [...e.selectedOptions].map(o=>o.textContent).join(',') : '')),
      x: c.x, y: c.y, vis: vis(e),
    });
  });

  const buttons = [];
  [...document.querySelectorAll('button, [role=button], a')].forEach((e) => {
    if (!vis(e)) return;
    const t = short(e.textContent);
    if (!t || t.length > 34) return;
    const c = ctr(e);
    buttons.push({ t, x: c.x, y: c.y, disabled: !!e.disabled });
  });

  // marker texts that matter for CP1 decisions (dedup, show coords)
  const markers = ['基本情報','価格設定','下書きを保存','提出を確認','審査に提出',
    'カードを保存しました','Capafy で実行','On-Demand','Subscription','Daily','Weekly','Monthly',
    'Add Plan','無料トライアル','Enable Free Trial','No Free Trial','重複するプラン',
    'メインカテゴリ','確認','ファイル','アップロード','スキル'];
  const found = {};
  [...document.querySelectorAll('*')].forEach((e) => {
    const t = (e.textContent || '').replace(/\s+/g,' ').trim();
    const r = e.getBoundingClientRect();
    if (r.height > 60 || r.height < 5 || !vis(e)) return;
    for (const m of markers) {
      if (t === m || (m.length > 6 && t.startsWith(m) && t.length < m.length + 8)) {
        if (!found[m]) { const c = ctr(e); found[m] = { x: c.x, y: c.y }; }
      }
    }
  });

  const toastOK = [...document.querySelectorAll('*')].some(e => /カードを保存しました/.test(e.textContent||''));
  // price tab svg color (green rgb(61,220,132)=ok)
  let priceSvg = '';
  const pt = [...document.querySelectorAll('button')].find(e => (e.textContent||'').trim() === '価格設定');
  if (pt) priceSvg = [...pt.querySelectorAll('svg')].map(s => getComputedStyle(s).color).join(',');

  return { url: location.href, scrollY: Math.round(scrollY), vh: innerHeight,
           fields, buttons: buttons.slice(0, 60), markers: found,
           toastOK, priceSvg, cardDone: /card-done|credential/.test(location.href) };
}
"""


def all_pages(br):
    out = []
    for c in br.contexts:
        out.extend(c.pages)
    return out


def get_page(br, prefer_capafy=True, create_ctx=None):
    pages = all_pages(br)
    if prefer_capafy:
        cap = [p for p in pages if 'capafy.ai' in (p.url or '')]
        if cap:
            return cap[-1]
    if pages:
        return pages[-1]
    ctx = create_ctx or (br.contexts[0] if br.contexts else br.new_context())
    return ctx.new_page()


def dump(pg, shot=True):
    st = pg.evaluate(STATE_JS)
    if shot:
        try:
            pg.screenshot(path=SHOT)
            st['shot'] = SHOT
        except Exception as e:
            st['shot_err'] = str(e)
    print(json.dumps(st, ensure_ascii=False, indent=1))


def main():
    if len(sys.argv) < 2:
        print("usage: cp1_agent.py <cmd> ..."); sys.exit(2)
    cmd = sys.argv[1]
    pw = sync_playwright().start()
    br = pw.chromium.connect_over_cdp(CDP)

    if cmd == "open":
        url = sys.argv[2]
        # reuse an existing capafy tab if present; otherwise create a BRAND-NEW tab.
        # NEVER hijack a daily-driver tab (its watchdog restores the original URL,
        # so a hijacked tab silently reverts). A fresh new_page persists.
        cap = [p for p in all_pages(br) if 'capafy.ai' in (p.url or '')]
        if cap:
            pg = cap[-1]
        else:
            ctx = br.contexts[0] if br.contexts else br.new_context()
            pg = ctx.new_page()
        pg.bring_to_front()
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(6)
        dump(pg); return

    pg = get_page(br, prefer_capafy=True)
    pg.bring_to_front()

    if cmd == "shot":
        dump(pg)
    elif cmd == "state":
        dump(pg, shot=False)
    elif cmd == "click":
        x, y = int(sys.argv[2]), int(sys.argv[3])
        pg.mouse.click(x, y); time.sleep(1.2); dump(pg)
    elif cmd == "clicktext":
        text = sys.argv[2]; nth = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        c = pg.evaluate(
            """(a)=>{const[t,n]=a;const els=[...document.querySelectorAll('*')].filter(e=>{const s=(e.textContent||'').replace(/\\s+/g,' ').trim();const r=e.getBoundingClientRect();return s===t&&r.height<60&&r.height>5&&r.width>0;});const e=els[n];if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};}""",
            [text, nth])
        if not c:
            print(json.dumps({"error": f"text not found: {text} (nth={nth})"})); return
        pg.mouse.click(c["x"], c["y"]); time.sleep(1.2); dump(pg)
    elif cmd == "fill":
        idx = int(sys.argv[2]); val = sys.argv[3]
        els = pg.query_selector_all("input, textarea, select")
        # rebuild the same visible-field order used in STATE_JS
        fields = [e for e in els if (e.get_attribute("type") == "file") or pg.evaluate("(e)=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'&&r.bottom>0&&r.top<innerHeight+400;}", e)]
        if idx >= len(fields):
            print(json.dumps({"error": f"field idx {idx} out of range ({len(fields)} fields)"})); return
        e = fields[idx]; e.scroll_into_view_if_needed(); e.click()
        try: e.fill(val)
        except Exception: e.fill(""); e.type(val, delay=12)
        time.sleep(0.5); dump(pg)
    elif cmd == "typeinto":
        idx = int(sys.argv[2]); val = sys.argv[3]
        els = pg.query_selector_all("input, textarea, select")
        fields = [e for e in els if (e.get_attribute("type") == "file") or pg.evaluate("(e)=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'&&r.bottom>0&&r.top<innerHeight+400;}", e)]
        if idx >= len(fields):
            print(json.dumps({"error": f"field idx {idx} out of range"})); return
        e = fields[idx]; e.scroll_into_view_if_needed(); e.click()
        try: e.fill("")
        except Exception: pass
        e.type(val, delay=14); time.sleep(0.5); dump(pg)
    elif cmd == "press":
        key = sys.argv[2]; pg.keyboard.press(key); time.sleep(0.6); dump(pg)
    elif cmd == "upload":
        idx = int(sys.argv[2]); path = sys.argv[3]
        fis = pg.query_selector_all("input[type=file]")
        if idx >= len(fis):
            print(json.dumps({"error": f"file input idx {idx} out of range ({len(fis)})"})); return
        fis[idx].set_input_files(path); time.sleep(4); dump(pg)
    elif cmd == "scroll":
        # Capafy's form scrolls an INNER container, not window -> use mouse wheel
        # over the form area. Positive dy scrolls down, negative up.
        dy = int(sys.argv[2])
        pg.mouse.move(700, 500)
        pg.mouse.wheel(0, dy); time.sleep(0.8); dump(pg)
    elif cmd == "into":
        # scroll an element with exact text into view (for off-screen targets)
        text = sys.argv[2]; nth = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        pg.evaluate(
            """(a)=>{const[t,n]=a;const els=[...document.querySelectorAll('*')].filter(e=>{const s=(e.textContent||'').replace(/\\s+/g,' ').trim();const r=e.getBoundingClientRect();return s===t&&r.height<60&&r.height>5;});if(els[n])els[n].scrollIntoView({block:'center'});}""",
            [text, nth]); time.sleep(0.6); dump(pg)
    elif cmd == "toast":
        st = pg.evaluate(STATE_JS)
        print(json.dumps({"toastOK": st["toastOK"], "cardDone": st["cardDone"],
                          "priceSvg": st["priceSvg"], "url": st["url"]}, ensure_ascii=False))
    else:
        print(f"unknown cmd: {cmd}"); sys.exit(2)


if __name__ == "__main__":
    main()
