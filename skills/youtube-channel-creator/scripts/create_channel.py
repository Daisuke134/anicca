#!/usr/bin/env python3
"""create_channel.py — create a YouTube Brand-Account channel on the daily-driver CloakBrowser
(CDP http://localhost:9222), handling the REAL end-to-end flow including the one-time phone
verification YouTube demands once the account already has channels. Battle-tested live 2026-06-29.

USAGE
  # Phase A — start: drives create → (advanced-features gate) → phone-verify step1 → sends SMS, exits.
  create_channel.py --name "Money Blueprint" --handle "moneyblueprintdaily" [--phone "$DAIS_PHONE"]
      → on success of step1 prints {"needs_code": true, ...}; an SMS is sent to <phone>.
  # Phase B — finish: enter the 6-digit SMS code, then create the channel (+ optional profile desc).
  create_channel.py --name "Money Blueprint" --handle "moneyblueprintdaily" --code 123456 [--desc "..."]

If the account needs NO phone verification (1st/2nd channel), Phase A creates the channel directly.

LEARNINGS baked in (run→learn→fix, 2026-06-29, on person@example.com):
  • Logged out → YouTube bounces to accounts.google.com; 2FA = "tap Yes on phone" (human, once).
    We detect this and report NOT_SIGNED_IN rather than failing silently.
  • 3rd+ channel pops "上級者向け機能を利用する" → 認証 → youtube.com/verify (phone, 1 number = 2/yr).
  • On the verify form the COUNTRY box may DISPLAY the phone number — that is NORMAL/valid (confirmed
    by Dais); just fill the 電話番号 field (placeholder contains "555") via the native value setter and
    click 次へ — it advances to step 2/2 and sends the SMS. (We still best-effort click 日本.)
  • Verify is 2 steps: step1 send SMS → step2 enter 6-digit code → 送信.
  • Create dialog inputs have NO type attribute → select `input`, filter `.type==='text'`, exclude the
    search box (placeholder 検索); fill via native setter + input/change events.
Outputs one JSON line; screenshots saved under /tmp/mine for evidence.
"""
import os, sys, time, json, argparse
from playwright.sync_api import sync_playwright

CDP = "http://localhost:9222"
SHOTDIR = "/tmp/mine"

def shot(pg, name):
    os.makedirs(SHOTDIR, exist_ok=True); p = f"{SHOTDIR}/{name}.png"
    try: pg.screenshot(path=p)
    except Exception: p = None
    return p

def find_page(ctx, must):
    return next((q for q in ctx.pages if must in q.url), None)

def fill_native(pg, finder_js, value):
    """finder_js returns the input element; set value via native setter so YouTube's framework sees it."""
    return pg.evaluate("""([fjs,val])=>{const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
        const el=(new Function('return ('+fjs+')()'))(); if(!el) return false; el.focus(); set.call(el,val);
        el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return true;}""",
        [finder_js, value])

PHONE_INPUT = "()=>[...document.querySelectorAll('input')].find(x=>x.placeholder&&x.placeholder.includes('555'))"
CODE_INPUT  = "()=>[...document.querySelectorAll('input')].find(x=>x.offsetParent&&x.placeholder!=='検索')"

def phone_verify_step1(pg, ctx, phone, out):
    vp = find_page(ctx, "youtube.com/verify")
    if not vp:
        pg.goto("https://www.youtube.com/verify", wait_until="domcontentloaded"); time.sleep(5); vp = pg
    vp.bring_to_front()
    # best-effort pick 日本 (the number-in-country-box display is FINE per learnings)
    try:
        vp.evaluate("""()=>{const o=[...document.querySelectorAll('yt-formatted-string,li,div')].find(e=>e.textContent.trim()==='日本'&&e.offsetParent&&e.children.length===0);if(o)o.click()}""")
        time.sleep(1)
    except Exception: pass
    fill_native(vp, PHONE_INPUT, phone); time.sleep(1)
    try: vp.get_by_text("次へ", exact=True).last.click(timeout=6000); time.sleep(6)
    except Exception as e: out["error"] = f"verify-next {type(e).__name__}"
    step2 = vp.evaluate("()=>document.body.innerText.includes('ステップ 2/2')")
    out["needs_code"] = bool(step2)
    out["stage"] = "sms-sent-awaiting-code" if step2 else "verify-step1-stuck"
    out["resume"] = f"re-run with --code <6 digits>  (SMS sent to {phone})"
    out["shot"] = shot(vp, "yt_verify_step2")

def phone_verify_step2(ctx, code, out):
    vp = find_page(ctx, "youtube.com/verify")
    if not vp:
        out["error"] = "no verify page open — run Phase A (no --code) first"; return False
    vp.bring_to_front()
    fill_native(vp, CODE_INPUT, code); time.sleep(1)
    try: vp.get_by_text("送信", exact=True).last.click(timeout=6000); time.sleep(7)
    except Exception as e: out["error"] = f"code-submit {type(e).__name__}"; out["shot"]=shot(vp,"yt_code_err"); return False
    out["verify_after"] = vp.url[:90]; return True

def open_create_dialog(pg, ctx, a, out):
    """returns 'dialog' if create inputs are present, 'gate' if advanced-verify gate hit, else None."""
    for _ in range(4):
        try: pg.get_by_text("チャンネルを作成", exact=False).first.click(timeout=4000)
        except Exception: pass
        time.sleep(3)
        if pg.evaluate("()=>document.body.innerText.includes('上級者向け機能')"):
            try: pg.get_by_text("認証", exact=True).last.click(timeout=5000); time.sleep(5)
            except Exception: pass
            return "gate"
        n = pg.evaluate("()=>[...document.querySelectorAll('input')].filter(i=>i.type==='text'&&i.placeholder!=='検索').length")
        if n >= 2: return "dialog"
    return None

def fill_and_create(pg, a, out):
    pg.evaluate("""([name,handle])=>{const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
        const ins=[...document.querySelectorAll('input')].filter(i=>i.type==='text'&&i.placeholder!=='検索');
        [name,handle].forEach((v,idx)=>{const el=ins[idx]; if(!el)return; set.call(el,v);
          el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));});}""", [a.name, a.handle])
    time.sleep(2)
    try: pg.get_by_text("チャンネルを作成", exact=True).last.click(timeout=5000)
    except Exception as e: out["error"] = f"create-click {type(e).__name__}"
    time.sleep(8)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True); ap.add_argument("--handle", required=True)
    ap.add_argument("--phone", default=os.environ.get("DAIS_PHONE"))
    ap.add_argument("--code", default=None); ap.add_argument("--desc", default=None)
    a = ap.parse_args()
    out = {"name": a.name, "handle": a.handle, "created": False}

    with sync_playwright() as p:
        ctx = p.chromium.connect_over_cdp(CDP).contexts[0]
        pg = find_page(ctx, "youtube.com") or ctx.new_page(); pg.bring_to_front()

        # Phase B: submit the SMS code first, then continue to create
        if a.code:
            if not phone_verify_step2(ctx, a.code, out): print(json.dumps(out)); return

        pg.goto("https://www.youtube.com/channel_switcher", wait_until="domcontentloaded"); time.sleep(5)
        if "accounts.google.com" in pg.url or "/signin" in pg.url:
            out["error"] = "NOT_SIGNED_IN (login: email+password+2FA tap on phone)"; out["shot"]=shot(pg,"yt_login"); print(json.dumps(out)); return

        if pg.evaluate("(h)=>document.body.innerText.includes('@'+h)", a.handle):
            out["created"]=True; out["url"]=f"https://www.youtube.com/@{a.handle}"; out["note"]="already existed"; out["shot"]=shot(pg,"yt_exists"); print(json.dumps(out)); return

        res = open_create_dialog(pg, ctx, a, out)
        if res == "gate":
            if a.code:  # already verified but gate re-shown — retry dialog
                res = open_create_dialog(pg, ctx, a, out)
            else:
                if not a.phone:
                    out["error"] = "PHONE_REQUIRED (--phone or DAIS_PHONE)"
                    print(json.dumps(out))
                    return
                phone_verify_step1(pg, ctx, a.phone, out); print(json.dumps(out)); return
        if res != "dialog":
            out["error"] = out.get("error","create dialog did not open"); out["shot"]=shot(pg,"yt_no_dialog"); print(json.dumps(out)); return

        fill_and_create(pg, a, out)
        pg.goto("https://www.youtube.com/channel_switcher", wait_until="domcontentloaded"); time.sleep(5)
        out["created"] = bool(pg.evaluate("(h)=>document.body.innerText.includes('@'+h)", a.handle))
        out["url"] = f"https://www.youtube.com/@{a.handle}"
        out["shot"] = shot(pg, "yt_after_create")
        if out["created"] and a.desc:
            out["profile_todo"] = "set description in YouTube Studio (extend script if needed)"
        print(json.dumps(out))

if __name__ == "__main__":
    main()
