#!/usr/bin/env python3
"""Fast, clean IG email-signup on the proxy browser (clean residential IP). Encodes every
gotcha learned 2026-07-17: dismiss the Cookie modal FIRST, fill all text fields via TRUSTED
typing (native-setter values don't commit to React state and get wiped on re-render), DOB via
trusted clicks on the custom combobox options, submit, then the caller enters the fresh OTP fast
(the code expires in ~30 min — do not dawdle). Reads creds from ~/.cloak/ig-<handle>.json.

Usage: CDP_PORT=9233 python3 ig_signup_proxy.py <handle>
Prints JSON progress per step; final line = {"stage":"otp_pending","tid":...} on success.
"""
import os, sys, time, json, importlib.util

HANDLE = sys.argv[1]
spec = importlib.util.spec_from_file_location("cdp", os.path.expanduser("~/.claude/skills/ig-account-create/scripts/cdp.py"))
cdp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdp)
C = json.load(open(os.path.expanduser(f"~/.cloak/ig-{HANDLE}.json")))


def ev(tid, js):
    return cdp.evaluate(tid, js)


def clickxy(tid, x, y):
    cdp.click_xy(tid, x, y)


def find_click_text(tid, text, tries=3):
    for _ in range(tries):
        r = ev(tid, f"""(()=>{{const b=[...document.querySelectorAll('[role=button],button,div')].find(e=>e.textContent.trim()==={json.dumps(text)}&&e.getBoundingClientRect().height>0&&e.offsetParent!==null);if(!b)return'{{}}';b.scrollIntoView({{block:'center'}});const r=b.getBoundingClientRect();return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}});}})()""")
        try:
            d = json.loads(r.strip().strip('"').replace('\\', ''))
        except Exception:
            d = {}
        if d.get("x"):
            time.sleep(0.3); clickxy(tid, d["x"], d["y"]); return True
        time.sleep(1)
    return False


def trusted_fill(tid, which, value):
    # focus the target visible input, then trusted-type (survives re-render, unlike native-setter)
    js = f"""(()=>{{const vis=[...document.querySelectorAll('input')].filter(i=>i.getBoundingClientRect().height>0);
      const texts=vis.filter(i=>i.type==='text'&&!i.getAttribute('aria-label'));let el;
      if('{which}'==='email')el=texts[0];else if('{which}'==='name')el=texts[1];else if('{which}'==='pw')el=vis.find(i=>i.type==='password');
      else if('{which}'==='user')el=vis.find(i=>(i.getAttribute('aria-label')||'').includes('ユーザーネーム'));
      if(!el)return'no';el.focus();try{{el.select()}}catch(e){{}}return'ok';}})()"""
    ev(tid, js); time.sleep(0.2)
    cdp.insert_text(tid, value); time.sleep(0.3)


def set_dob_field(tid, combo_label, option_text):
    # open the combobox, then scroll+click the option (trusted). Retry a few times.
    for attempt in range(4):
        r = ev(tid, f"""(()=>{{const c=[...document.querySelectorAll('[role=combobox]')].find(e=>(e.getAttribute('title')||'').includes({json.dumps(combo_label)})&&e.offsetParent!==null);if(!c)return'{{}}';const r=c.getBoundingClientRect();return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}});}})()""")
        try:
            d = json.loads(r.strip().strip('"').replace('\\', ''))
        except Exception:
            d = {}
        if not d.get("x"):
            return False
        clickxy(tid, d["x"], d["y"]); time.sleep(1.1)
        o = ev(tid, f"""(()=>{{const o=[...document.querySelectorAll('[role=option]')].filter(e=>e.offsetParent!==null).find(e=>e.textContent.trim()==={json.dumps(option_text)});if(!o)return'{{}}';o.scrollIntoView({{block:'center'}});const r=o.getBoundingClientRect();return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}});}})()""")
        try:
            od = json.loads(o.strip().strip('"').replace('\\', ''))
        except Exception:
            od = {}
        if od.get("y", 0) > 0:
            clickxy(tid, od["x"], od["y"]); time.sleep(0.7); return True
        time.sleep(0.5)
    return False


def main():
    tid = cdp.new_tab("https://www.instagram.com/accounts/emailsignup/") if hasattr(cdp, "new_tab") else None
    if not tid:
        # fallback to cdp.py 'new' via its function name
        tid = cdp.open_new(("https://www.instagram.com/accounts/emailsignup/")) if hasattr(cdp, "open_new") else None
    print(json.dumps({"stage": "opened", "tid": tid}), flush=True)
    time.sleep(6)
    # 1. dismiss cookie modal (must be first)
    got = find_click_text(tid, "すべてのCookieを許可")
    print(json.dumps({"stage": "cookie", "dismissed": got}), flush=True); time.sleep(1.5)
    # 2. fill all fields via trusted typing
    trusted_fill(tid, "email", C["email"])
    trusted_fill(tid, "name", C["name"])
    trusted_fill(tid, "pw", C["pw"])
    trusted_fill(tid, "user", C["username"])
    time.sleep(2)
    # 3. DOB
    y = set_dob_field(tid, "年", "1996年")
    m = set_dob_field(tid, "月", "6月")
    dd = set_dob_field(tid, "日", "15日")
    print(json.dumps({"stage": "dob", "year": y, "month": m, "day": dd}), flush=True)
    # 4. re-verify fields (username often needs re-type after DOB) + check state
    st = ev(tid, """(()=>{const vis=[...document.querySelectorAll('input')].filter(i=>i.getBoundingClientRect().height>0);const t=vis.filter(i=>i.type==='text'&&!i.getAttribute('aria-label'));const pw=vis.find(i=>i.type==='password');const u=vis.find(i=>(i.getAttribute('aria-label')||'').includes('ユーザーネーム'));return JSON.stringify({email:t[0]?t[0].value.length:0,name:t[1]?t[1].value.length:0,pw:pw?pw.value.length:0,user:u?u.value:''});})()""")
    sd = json.loads(st.strip().strip('"').replace('\\', ''))
    if sd.get("email", 0) == 0:
        trusted_fill(tid, "email", C["email"])
    if sd.get("name", 0) == 0:
        trusted_fill(tid, "name", C["name"])
    if sd.get("pw", 0) == 0:
        trusted_fill(tid, "pw", C["pw"])
    if sd.get("user", "") != C["username"]:
        trusted_fill(tid, "user", C["username"])
    time.sleep(2)
    print(json.dumps({"stage": "prefilled", "state": sd}), flush=True)
    # 5. submit
    find_click_text(tid, "送信")
    time.sleep(7)
    scr = ev(tid, """(()=>{const t=[...document.querySelectorAll('span,div,h1,h2')].filter(e=>e.children.length===0&&e.textContent.trim().length>2&&e.getBoundingClientRect().height>0).map(e=>e.textContent.trim()).slice(0,4);return JSON.stringify(t);})()""")
    print(json.dumps({"stage": "submitted", "tid": tid, "screen": scr}), flush=True)


if __name__ == "__main__":
    main()
