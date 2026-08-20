"""Reliable X-Articles draft: type-and-chunk insertion (text chunk -> image -> text chunk -> ...).
Guarantees image ORDER (cursor always at end; no racy block-index click). Fresh draft. NEVER publishes."""
import os,time,json,subprocess,tempfile,sys
from playwright.sync_api import sync_playwright
W=os.path.expanduser("~/.cloak/note-work")
CLIP=os.environ["WRITER_X_CLIPBOARD_HELPER"]
HOMEPY=sys.executable
PARSED=os.environ["X_PARSED"]
d=json.load(open(PARSED)); TITLE=d["title"]; THUMB=d.get("cover_image",""); html=d["html"]
cis=sorted(d["content_images"], key=lambda c:c["block_index"])
# split html into chunks at each image's anchor paragraph end
chunks=[]; pos=0
for ci in cis:
    at=ci["after_text"] or ""
    idx=html.find(at,pos)
    if idx==-1 and len(at)>20: idx=html.find(at[:20],pos)
    if idx==-1:
        print("ANCHOR NOT FOUND:",at[:30]); continue
    end=html.find("</p>",idx)
    end = (end+4) if end!=-1 else len(html)
    chunks.append(("html",html[pos:end])); chunks.append(("img",ci["path"])); pos=end
chunks.append(("html",html[pos:]))
print("chunks:",len(chunks),"images:",sum(1 for k,_ in chunks if k=='img'))

DETECT="""()=>{const t=[...document.querySelectorAll('textarea')].find(e=>{const a=((e.getAttribute('aria-label')||'')+(e.placeholder||'')).toLowerCase();const b=e.getBoundingClientRect();return a.includes('title')||(b.height>40&&b.width>300&&b.y<700&&b.x>900);});if(!t)return null;const b=t.getBoundingClientRect();return {x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)};}"""
def clip_html(s):
    f=tempfile.NamedTemporaryFile("w",suffix=".html",delete=False); f.write(s); f.close()
    subprocess.run([HOMEPY,CLIP,"html","--file",f.name],capture_output=True)
def clip_img(p): subprocess.run([HOMEPY,CLIP,"image",p],capture_output=True)
p=sync_playwright().start(); b=p.chromium.connect_over_cdp("http://localhost:9222"); pg=b.contexts[0].new_page()
def upwait():
    for _ in range(20):
        if not pg.evaluate("()=>/Uploading|アップロード|正在上传/.test(document.body.innerText)"): break
        time.sleep(1)
try:
    pg.goto("https://x.com/compose/articles",wait_until="domcontentloaded",timeout=50000); time.sleep(5)
    pg.evaluate("""()=>{const b=[...document.querySelectorAll('button,a,div[role=button],span')].find(x=>(x.textContent||'').trim()==='Write');if(b)b.click();}""")
    pos2=None
    for i in range(30):
        pos2=pg.evaluate(DETECT)
        if pos2: break
        if i==12: pg.evaluate("""()=>{const b=[...document.querySelectorAll('button,a,div[role=button],span')].find(x=>(x.textContent||'').trim()==='Write');if(b)b.click();}""")
        time.sleep(1)
    if not pos2: raise SystemExit("no editor")
    pg.mouse.click(pos2['x'],pos2['y']); time.sleep(0.6); pg.keyboard.type(TITLE,delay=6); time.sleep(1.5)
    DRAFT=pg.url
    pg.query_selector('[data-testid="composer"]').click(); time.sleep(0.8)
    for k,v in chunks:
        if k=="html":
            if not v.strip(): continue
            clip_html(v); pg.keyboard.press("Meta+v"); time.sleep(2.0)
        else:
            if not os.path.exists(v): print("img missing",v); continue
            n0=pg.evaluate("()=>document.querySelector('[data-testid=composer]').querySelectorAll('img').length")
            ok=False
            for attempt in range(3):
                clip_img(v); time.sleep(0.4); pg.keyboard.press("Meta+v"); time.sleep(2.8); upwait()
                if pg.evaluate("()=>document.querySelector('[data-testid=composer]').querySelectorAll('img').length")>n0:
                    ok=True; break
                time.sleep(1.0)
            if not ok: print("IMG PASTE FAILED after retries:",v)
    # cover
    fis=pg.query_selector_all('input[type=file]')
    if fis and THUMB and os.path.exists(THUMB):
        fis[0].set_input_files(THUMB); time.sleep(5)
        pg.evaluate("""()=>{const a=[...document.querySelectorAll('button,div[role=button],span')].find(x=>['Apply','適用','保存','Save'].includes((x.textContent||'').trim()));if(a)a.click();}"""); time.sleep(3)
    nimg=pg.evaluate("()=>document.querySelector('[data-testid=composer]').querySelectorAll('img').length")
    print("imgs in composer:",nimg)
    print("DRAFT_URL:",DRAFT)
    pg.close()
finally:
    b=None
