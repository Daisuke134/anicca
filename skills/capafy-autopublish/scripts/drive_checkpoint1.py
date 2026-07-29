#!/usr/bin/env python3
"""Drive Capafy Web Checkpoint 1 (Agent Card edit) via camofox REST.

Reuses the exact recipe that shipped capafy-autopublish + reelfarm on
2026-06-04: open tab → Deselect-All → fill title/short/email/details via
React-native value setter → canvas-generated logo → Crop Save → pick
category → switch to Download mode → set price + DPA → Confirm Submit →
verify page=card-done.

usage: drive_checkpoint1.py <review_url> <selections.json>
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path


CAMOFOX = "http://localhost:9377"
USER = "anicca"
SESSION = "default"


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{CAMOFOX}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{CAMOFOX}{path}", timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def snap(tab: str) -> str:
    d = _get(f"/tabs/{tab}/snapshot?userId={USER}&sessionKey={SESSION}")
    return d.get("snapshot", "")


def click(tab: str, ref: str) -> None:
    _post(f"/tabs/{tab}/click", {"userId": USER, "sessionKey": SESSION, "ref": ref})


def press(tab: str, key: str) -> None:
    _post(f"/tabs/{tab}/press", {"userId": USER, "sessionKey": SESSION, "key": key})


def type_keyboard(tab: str, text: str, delay: int = 35) -> None:
    """Real keystrokes into the focused element — required for React-Hook-Form
    fields whose validation only updates on genuine input events. JS native
    value setters leave RHF's internal state stale, so the title length check
    keeps the 67-char LM-generated default and Confirm Submit silently no-ops
    (verified 2026-06-12)."""
    _post(
        f"/tabs/{tab}/type",
        {"userId": USER, "sessionKey": SESSION, "mode": "keyboard",
         "text": text, "delay": delay},
    )


def real_type_title(tab: str, ref: str, value: str) -> None:
    """Focus title field, select-all + delete, then type the value for real."""
    click(tab, ref)
    time.sleep(0.4)
    press(tab, "Meta+a")
    press(tab, "Delete")
    time.sleep(0.3)
    type_keyboard(tab, value)
    time.sleep(0.5)


def evaluate(tab: str, expr: str, awaitable: bool = False) -> object:
    body = {"userId": USER, "sessionKey": SESSION, "expression": expr}
    if awaitable:
        body["awaitPromise"] = True
    out = _post(f"/tabs/{tab}/evaluate", body)
    if not out.get("ok"):
        raise RuntimeError(f"evaluate failed: {out}")
    return out.get("result")


def open_tab(url: str) -> str:
    out = _post(
        "/tabs",
        {"url": url, "userId": USER, "sessionKey": SESSION},
    )
    tab = out.get("tabId", "")
    if not tab:
        raise RuntimeError(f"open_tab failed: {out}")
    return tab


def find_ref(s: str, label: str) -> str | None:
    m = re.search(rf'button\s+"{re.escape(label)}[^"]*"\s+\[e(\d+)\]', s)
    return f"e{m.group(1)}" if m else None


def main(argv: list[str]) -> int:
    review_url, selections_path = argv[1], argv[2]
    sel = json.loads(Path(selections_path).read_text())
    aux = json.loads(
        (Path.home() / ".cache" / "anicca-capafy" / "selections-aux.json").read_text()
    )
    title = sel["title"]
    short = sel["description"]
    details = aux["details"]
    category = aux["category"]
    email = "contact@aniccaai.com"
    price = "9.99"

    tab = open_tab(review_url)
    time.sleep(4)
    s = snap(tab)

    # ── Deselect All (workspace docs leak guard)
    ds = find_ref(s, "Deselect All")
    if ds:
        click(tab, ds)
        time.sleep(1)

    # ── Open Basic Info
    bi = find_ref(s, "Basic Info")
    if bi:
        click(tab, bi)
        time.sleep(1)

    # ── Fill title / short / email / details via React-safe native setter
    js = """(()=>{
      const setV=(el,v)=>{
        const p=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(p,'value').set.call(el,v);
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
      };
      const inputs=document.querySelectorAll('input[type="text"],input:not([type]),input[type="email"]');
      const tas=document.querySelectorAll('textarea');
      const titleEl=Array.from(inputs).find(i=>i.placeholder&&i.placeholder.toLowerCase().includes('agent name'));
      const emailEl=Array.from(inputs).find(i=>i.placeholder&&i.placeholder.toLowerCase().includes('support@'));
      const shortEl=Array.from(tas).find(t=>t.placeholder&&t.placeholder.toLowerCase().includes('one paragraph'));
      const detEl=Array.from(tas).find(t=>t.placeholder&&t.placeholder.toLowerCase().includes('sample inputs'));
      const T=__T__,S=__S__,E=__E__,D=__D__;
      const r={};
      if(titleEl){setV(titleEl,T);r.t=T.length;}else r.t='NF';
      if(shortEl){setV(shortEl,S);r.s=S.length;}else r.s='NF';
      if(emailEl){setV(emailEl,E);r.e=1;}else r.e='NF';
      if(detEl){setV(detEl,D);r.d=D.length;}else r.d='NF';
      return JSON.stringify(r);
    })()""".replace("__T__", json.dumps(title)) \
         .replace("__S__", json.dumps(short)) \
         .replace("__E__", json.dumps(email)) \
         .replace("__D__", json.dumps(details))
    res = evaluate(tab, js)
    print(f"[cp1] fields: {res}", file=sys.stderr)

    # ── Re-enter the Title with REAL keystrokes so React-Hook-Form registers
    # the (short) value and clears the "Title cannot exceed 50 characters"
    # validation left by the 67-char LM-generated default. Without this the
    # native-setter value above is invisible to RHF and Confirm Submit no-ops.
    s2 = snap(tab)
    tm = re.search(r'textbox\s+"Agent name[^"]*"\s+\[e(\d+)\]', s2)
    if tm:
        real_type_title(tab, f"e{tm.group(1)}", title[:50])
        chk = re.search(r"Title \* (\d+) / 50", snap(tab))
        print(f"[cp1] title real-typed -> {chk.group(1) if chk else '?'} / 50",
              file=sys.stderr)

    # ── Logo: canvas → File → DataTransfer → file input
    initial = title.split("—")[0].strip()[:14] or category[:8]
    js_logo = """(()=>{
      const c=document.createElement('canvas');c.width=512;c.height=512;
      const g=c.getContext('2d');
      const gr=g.createLinearGradient(0,0,512,512);
      gr.addColorStop(0,'#1f2440');gr.addColorStop(1,'#0e1224');
      g.fillStyle=gr;g.fillRect(0,0,512,512);
      g.strokeStyle='#ff8c42';g.lineWidth=14;g.strokeRect(28,28,456,456);
      g.fillStyle='#ff8c42';g.font='bold 90px -apple-system, system-ui, sans-serif';
      g.textAlign='center';g.textBaseline='middle';
      g.fillText(__INI__,256,256);
      g.fillStyle='#ffffff';g.font='bold 44px -apple-system, system-ui, sans-serif';
      g.fillText('Anicca',256,460);
      const u=c.toDataURL('image/png');
      const b=atob(u.split(',')[1]);const a=new Uint8Array(b.length);
      for(let i=0;i<b.length;i++)a[i]=b.charCodeAt(i);
      const f=new File([a],'logo.png',{type:'image/png'});
      const inp=document.querySelector('input[type=file]');
      if(!inp)return'NO';
      const dt=new DataTransfer();dt.items.add(f);
      inp.files=dt.files;inp.dispatchEvent(new Event('change',{bubbles:true}));
      return 'logo:'+f.size;
    })()""".replace("__INI__", json.dumps(initial))
    evaluate(tab, js_logo)
    time.sleep(2)

    # ── Crop dialog: click Save
    s = snap(tab)
    m = re.search(r'dialog\s+"Crop[^"]*"[\s\S]*?button\s+"Save"\s+\[e(\d+)\]', s)
    if m:
        click(tab, f"e{m.group(1)}")
        time.sleep(2)

    # ── Pick Primary Category (open dropdown, click matching button)
    s = snap(tab)
    m = re.search(
        r'Primary category[\s\S]{1,120}?button\s+"Choose an option"\s+\[e(\d+)\]', s
    )
    if m:
        click(tab, f"e{m.group(1)}")
        time.sleep(2)
        s = snap(tab)
        cm = re.search(rf'button\s+"{re.escape(category)}"\s+\[e(\d+)\]', s)
        if not cm:
            # Fall back to Engineering if our preferred category isn't visible
            cm = re.search(r'button\s+"Engineering"\s+\[e(\d+)\]', s)
        if cm:
            click(tab, f"e{cm.group(1)}")
            time.sleep(1)

    # ── Switch to Pricing tab
    s = snap(tab)
    pt = find_ref(s, "Pricing")
    if pt:
        click(tab, pt)
        time.sleep(2)

    # ── Choose Download mode + set price + DPA
    s = snap(tab)
    dm = re.search(r'button\s+"Download[\s\S]*?"\s+\[e(\d+)\]', s)
    if dm:
        click(tab, f"e{dm.group(1)}")
        time.sleep(2)
    js_price = """(()=>{
      const setV=(el,v)=>{
        const p=HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(p,'value').set.call(el,v);
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
      };
      const sb=document.querySelector('input[type=number]');
      if(!sb)return'NO_SB';
      setV(sb,__P__);
      const cbs=document.querySelectorAll('input[type=checkbox]');
      const dpa=Array.from(cbs).find(c=>{
        const l=c.closest('label')||c.parentElement;
        return l&&/Data Processing Agreement/.test(l.textContent||'');
      })||cbs[cbs.length-1];
      if(dpa&&!dpa.checked)dpa.click();
      return 'p='+sb.value+' dpa='+(dpa?dpa.checked:'NF');
    })()""".replace("__P__", json.dumps(price))
    print(f"[cp1] pricing: {evaluate(tab, js_price)}", file=sys.stderr)

    # ── Confirm Submit — React handler only fires via element.click() in page JS;
    # camofox /click ref does not navigate (verified 2026-06-04). Click once to open
    # the Submit-for-Review modal, wait for mount, then click the exact-text button again.
    js_submit = """(()=>{
      const byText=t=>Array.from(document.querySelectorAll('button')).find(b=>(b.textContent||'').trim()===t);
      const sub=byText('Confirm Submit')||byText('Submit for Review')||byText('Submit');
      if(!sub)return'NO_SUBMIT';
      sub.click();
      return 'CLICKED:'+(sub.textContent||'').trim();
    })()"""
    print(f"[cp1] submit#1: {evaluate(tab, js_submit)}", file=sys.stderr)
    time.sleep(2)
    print(f"[cp1] submit#2: {evaluate(tab, js_submit)}", file=sys.stderr)
    time.sleep(5)

    # ── Verify page=card-done
    d = _get(f"/tabs/{tab}/snapshot?userId={USER}&sessionKey={SESSION}")
    if "card-done" not in d.get("url", "") and "Agent Card Saved" not in d.get("snapshot", ""):
        raise RuntimeError(
            f"checkpoint1 did not transition to card-done. url={d.get('url')!r}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
