#!/usr/bin/env python3
"""
drive_checkpoint2.py — Capafy CP2 (credential hosting) automation.

Sets the LLM Config to the CANONICAL recipe (verified 2026-06-25):
  Base URL = https://openrouter.ai/api/v1
  Model    = anthropic/claude-sonnet-4.6   (real Claude Sonnet 4.6 = what all winners use)
  API Key  = $CAPAFY_HOST_OPENROUTER_KEY   (Life Manager state env)
  Format   = openai-responses (Capafy default; OpenRouter /responses verified working)
Deletes the blockrun (127.0.0.1 localhost) card which always fails verification.
Clicks "キーを確認して保存" and waits for the "キー確認済み" success toast.

Usage: drive_checkpoint2.py <CP2_review_url>
Requires: CloakBrowser daemon on CDP :9222 (never close it), CAPAFY_HOST_OPENROUTER_KEY in env.
Exit 0 + prints VERIFIED on success; exit 1 on failure (fail-closed).
"""
import os, sys, time, json, urllib.request
from playwright.sync_api import sync_playwright

BASE_URL = "https://openrouter.ai/api/v1"
MODEL    = "anthropic/claude-sonnet-4.6"

def _detect_cdp():
    """CDP port drifts (observed 9222 -> 9223) — auto-detect instead of trusting
    a hardcoded port (self-fix-capafy-loop, 2026-07-21)."""
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
    return "http://localhost:9222"

def main():
    if len(sys.argv) < 2:
        print("ERR: need CP2 url"); sys.exit(1)
    cp2 = sys.argv[1]
    key = os.environ.get("CAPAFY_HOST_OPENROUTER_KEY", "").strip()
    if not key:
        # fallback: read from the per-user Life Manager state env
        try:
            state_home = os.environ.get(
                "LIFE_MANAGER_STATE_HOME",
                os.path.expanduser("~/.local/state/life-manager"),
            )
            for ln in open(os.path.join(state_home, ".env")):
                if ln.startswith("CAPAFY_HOST_OPENROUTER_KEY="):
                    key = ln.split("=", 1)[1].strip(); break
        except Exception:
            pass
    if not key:
        print("ERR: CAPAFY_HOST_OPENROUTER_KEY missing"); sys.exit(1)

    p = sync_playwright().start()
    b = p.chromium.connect_over_cdp(_detect_cdp())
    # Reuse an existing capafy tab; else create a BRAND-NEW tab. NEVER hijack a
    # daily-driver tab (ctx.pages[0] may be coconala/discord/etc and its watchdog
    # reverts a hijacked URL -> silent CP2 failure).
    allpg = [pg for c in b.contexts for pg in c.pages]
    cap = [pg for pg in allpg if 'capafy.ai' in (pg.url or '')]
    if cap:
        pg = cap[-1]
    else:
        ctx = b.contexts[0] if b.contexts else b.new_context()
        pg = ctx.new_page()
    pg.bring_to_front()
    pg.goto(cp2, wait_until="domcontentloaded", timeout=60000); time.sleep(7)

    # expand 検出されたキー if collapsed
    if not pg.evaluate("""()=>[...document.querySelectorAll('input')].some(i=>/apiKey/.test(i.value||''))"""):
        pg.evaluate("""()=>{const e=[...document.querySelectorAll('*')].find(x=>/検出されたキー/.test((x.textContent||''))&&x.getBoundingClientRect().height<60&&x.getBoundingClientRect().width<400);if(e)e.click();}""")
        time.sleep(1.5)

    # CRITICAL: the LLM card is often in SUMMARY mode (shows Base URL/Model as text, no inputs).
    # Click its Edit pencil (first button in the card) to enter edit mode, else field-setting finds nothing.
    has_input = pg.evaluate("""()=>[...document.querySelectorAll('input')].some(i=>{const v=i.value||'';return v.indexOf('api.')>-1||v.indexOf('openrouter')>-1;})""")
    if not has_input:
        pg.evaluate(r"""()=>{const t=[...document.querySelectorAll('*')].find(e=>/^models\.providers\.[a-z_]+\.apiKey$/.test((e.textContent||'').trim()));if(t){let c=t;for(let k=0;k<10;k++){c=c.parentElement;if(!c)break;if(c.querySelectorAll('button').length&&c.getBoundingClientRect().height>120)break;}const bs=[...c.querySelectorAll('button')];if(bs.length)bs[0].click();}}""")
        time.sleep(2)

    # set Base URL (the input currently holding api.openai.com or api.anthropic.com)
    def setfield(match_substrs, val):
        for i in pg.query_selector_all("input"):
            v = i.get_attribute("value") or ""; ph = i.get_attribute("placeholder") or ""
            if any(s in v for s in match_substrs) or any(s in ph for s in match_substrs):
                i.scroll_into_view_if_needed(); i.click(); i.fill(""); i.fill(val); return True
        return False
    print("baseurl:", setfield(["api.openai.com", "api.anthropic.com", "openrouter.ai", "api.deepseek", "127.0.0.1"], BASE_URL))

    # model field
    mset = False
    for i in pg.query_selector_all("input"):
        v = i.get_attribute("value") or ""; ph = i.get_attribute("placeholder") or ""
        if v.startswith("gpt-") or v.startswith("claude-") or v.startswith("anthropic/") or v == "auto" or ph == "Model":
            i.scroll_into_view_if_needed(); i.click(); i.fill(""); i.type(MODEL, delay=10); time.sleep(0.6)
            pg.keyboard.press("Enter"); mset = True; break
    print("model:", mset)

    # api key
    ak = pg.query_selector("input[placeholder*='Paste'], input[placeholder*='key']")
    if ak:
        ak.scroll_into_view_if_needed(); ak.click(); ak.fill(key); print("key pasted len", len(ak.input_value()))

    # ★ commit the LLM card. It is often in EDIT mode (Base URL/Model/Key inputs
    #   shown) — a card-level "Save"/"保存" button MUST be clicked to commit, else
    #   "キーを確認して保存" stays DISABLED. Scroll each Save into view and click. ★
    def click_card_save():
        return pg.evaluate("""()=>{const bs=[...document.querySelectorAll('button')].filter(e=>['Save','保存'].includes((e.textContent||'').trim()));for(const bt of bs){bt.scrollIntoView({block:'center'});bt.click();return true;}return false;}""")
    click_card_save(); time.sleep(2)

    # delete blockrun (localhost) card (always fails verification)
    pg.evaluate(r"""()=>{
      const t=[...document.querySelectorAll('*')].find(e=>(e.textContent||'').trim()==='models.providers.blockrun.apiKey');
      if(!t) return;
      let card=t; for(let k=0;k<10;k++){card=card.parentElement;if(!card)break;const h=card.getBoundingClientRect().height;if(h>150&&h<420)break;}
      const btns=[...card.querySelectorAll('button')]; if(btns.length){btns[btns.length-1].click();}
    }""")
    time.sleep(1.2)

    # final verify: click キーを確認して保存 once ENABLED. If disabled, the card is
    # still uncommitted -> click its Save again and retry (up to 4 rounds).
    def verify_click():
        return pg.evaluate("""()=>{const bs=[...document.querySelectorAll('button')].filter(e=>/キーを確認して保存/.test((e.textContent||'')));const bt=bs[bs.length-1];if(!bt)return 'nf';if(bt.disabled)return 'disabled';bt.scrollIntoView({block:'center'});bt.click();return 'clicked';}""")
    sv = "?"
    for _ in range(4):
        sv = verify_click()
        if sv == "clicked":
            break
        if sv == "disabled":
            click_card_save(); time.sleep(2)
        else:
            break
    print("save:", sv)
    result = "TIMEOUT"
    for _ in range(10):
        time.sleep(3)
        toast = pg.evaluate("""()=>{const t=[...document.querySelectorAll('*')].map(e=>(e.textContent||'').trim()).find(x=>/キー確認済み|Verification failed|失敗|エラー/i.test(x)&&x.length<120);return t||'';}""")
        url = pg.evaluate("()=>location.href")
        if "キー確認済み" in toast or "credential-done" in url:
            result = "VERIFIED"; break
        if "Verification failed" in toast or "失敗" in toast:
            result = "FAILED: " + toast[:80]; break
    print("RESULT:", result)
    sys.exit(0 if result == "VERIFIED" else 1)

if __name__ == "__main__":
    main()
