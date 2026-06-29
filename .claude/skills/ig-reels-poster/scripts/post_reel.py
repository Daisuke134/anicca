#!/usr/bin/env python3
"""ig-reels-poster — publish a VIDEO Reel to Instagram via the CloakBrowser daily-driver.

★ MANUALLY VERIFIED E2E 2026-06-29 ★ on @aishigoto.labo (posted reel DaKIoaeuWiJ,
then deleted it via the browser — profile back to 投稿0件).

THE KEY TECHNIQUE (why a naive setFile fails on IG):
  IG's composer dropzone ignores DOM.setFileInputFiles on the static <input>.
  You MUST: Page.setInterceptFileChooserDialog(enabled) → click "コンピューターから選択"
  → catch Page.fileChooserOpened → DOM.setFileInputFiles on its backendNodeId.

Verified flow:
  新規投稿(+) → [intercept] コンピューターから選択 → 切り取る → 次へ →
  「新しいリール動画」 caption screen → caption + header シェア → ~30s processing → LIVE.
Delete:  reel url → ⋯ (他のオプション) → 削除 → confirm 削除.

Usage:
  post_reel.py --video <mp4> --caption-file <txt> --handle <ig_handle> [--live] [--delete-after]
  default = dry (loads video, fills caption, stops before シェア, discards).
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
import cdp  # noqa: E402
from websocket import create_connection  # noqa: E402

SHOTDIR = "/tmp/ig-reels-shots"; os.makedirs(SHOTDIR, exist_ok=True)


def ev(tid, e):
    r = cdp.evaluate(tid, e)
    return None if (isinstance(r, dict) and "__error__" in r) else r


def rect_center(tid, js_find):
    return ev(tid, js_find)


def shot(tid, n):
    p = os.path.join(SHOTDIR, f"{n}.png")
    try: cdp.screenshot(tid, p)
    except Exception: pass
    return p


def load_video_via_filechooser(tid, video):
    """The ONLY reliable way to put a video into IG's web composer."""
    ws = create_connection(cdp.page_ws(tid), timeout=30, suppress_origin=True, max_size=None)
    def send(i, m, p=None): ws.send(json.dumps({"id": i, "method": m, "params": p or {}}))
    def wait(idv=None, evt=None, t=15):
        end = time.time() + t
        while time.time() < end:
            ws.settimeout(max(0.1, end - time.time()))
            try: msg = json.loads(ws.recv())
            except Exception: break
            if idv and msg.get("id") == idv: return msg
            if evt and msg.get("method") == evt: return msg
        return None
    try:
        send(1, "DOM.enable"); send(2, "Page.enable"); send(3, "Runtime.enable"); time.sleep(0.8)
        send(10, "Page.setInterceptFileChooserDialog", {"enabled": True}); time.sleep(0.4)
        send(11, "Runtime.evaluate", {"expression":
            "(()=>{const b=[...document.querySelectorAll('button,[role=button],div[role=button]')]"
            ".find(x=>(x.textContent||'').trim()==='コンピューターから選択');if(b){b.click();return true}return false})()"})
        fc = wait(evt="Page.fileChooserOpened", t=10)
        if not fc:
            return False
        send(20, "DOM.setFileInputFiles", {"files": [video], "backendNodeId": fc["params"]["backendNodeId"]})
        wait(idv=20, t=10)
        send(30, "Page.setInterceptFileChooserDialog", {"enabled": False})
        return True
    finally:
        ws.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--handle", required=True, help="IG handle to verify the post landed")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--delete-after", action="store_true", help="delete the post after verifying (for test runs)")
    ap.add_argument("--tid", default=None, help="reuse an existing logged-in tab (e.g. an incognito-context TID where the target account is logged in). If omitted, opens a new tab in the default context.")
    a = ap.parse_args()
    video = os.path.abspath(a.video); assert os.path.exists(video)
    caption = open(a.caption_file, encoding="utf-8").read().strip()
    res = {"video": os.path.basename(video), "handle": a.handle, "live": a.live, "reached": "start", "published": False}
    try:
        if a.tid:
            tid = a.tid; cdp.navigate(tid, "https://www.instagram.com/")
        else:
            tid = cdp.new_tab("https://www.instagram.com/")
        time.sleep(7)
        if ev(tid, "(()=>!!document.querySelector('input[name=\"username\"],input[name=\"email\"]'))()"):
            res["error"] = "not logged in"; print(json.dumps(res)); return
        # dismiss fresh-account interstitials (お知らせをオンにする / アプリを保存 etc.) that block the composer
        for label in ["後で", "今はしない", "Not Now", "あとで", "キャンセル"]:
            d = rect_center(tid, """(()=>{const e=[...document.querySelectorAll('button,div[role=button],span,a')].find(x=>(x.textContent||'').trim()==='%s'&&x.getBoundingClientRect().height>0);if(!e)return null;const r=e.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""" % label)
            if d: cdp.click_xy(tid, d["x"], d["y"]); time.sleep(1.5); break
        # ★ ACCOUNT GUARD (CRITICAL): never post to the wrong account. ★
        # IG multi-account defaults to whichever account is active; if it isn't --handle, ABORT
        # (a 2026-06-29 incident posted to the wrong account because the active one wasn't checked).
        active = ev(tid, """(()=>{const a=document.querySelector('a[href^="/"] img[alt$="のプロフィール写真"]');if(a){const m=a.getAttribute('alt').match(/^(.+?)のプロフィール写真/);if(m)return m[1];}const s=[...document.querySelectorAll('span,div')].map(x=>(x.textContent||'').trim()).find(t=>/^[a-z0-9._]{2,30}$/.test(t)&&document.body.innerText.includes(t+'\\n'));return s||null;})()""")
        if active and active != a.handle:
            res["error"] = f"ACCOUNT GUARD: active account is '{active}', not '{a.handle}' — aborting to avoid posting to the wrong account"
            res["active_account"] = active; print(json.dumps(res, ensure_ascii=False)); return
        # 1) open composer
        c = rect_center(tid, """(()=>{const s=document.querySelector('svg[aria-label="新しい投稿"],svg[aria-label="New post"]');if(!s)return null;const r=s.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
        if not c: res["error"] = "no create btn"; print(json.dumps(res)); return
        cdp.click_xy(tid, c["x"], c["y"]); time.sleep(2.5)
        pm = rect_center(tid, """(()=>{const b=[...document.querySelectorAll('[role=button],button,div[role=button]')].find(x=>['投稿','Post'].includes((x.textContent||'').trim())&&x.offsetParent);if(!b)return null;const r=b.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
        if pm: cdp.click_xy(tid, pm["x"], pm["y"]); time.sleep(2)
        res["reached"] = "composer"; shot(tid, "1-composer")
        # 2) load video via file-chooser intercept (THE key step)
        if not load_video_via_filechooser(tid, video):
            res["error"] = "file chooser load failed"; shot(tid, "2-loadfail"); print(json.dumps(res)); return
        # wait for upload (次へ appears)
        ok = False
        for _ in range(12):
            time.sleep(5)
            if ev(tid, "(()=>!![...document.querySelectorAll('div[role=button],button,span,a')].find(x=>['次へ','Next'].includes((x.textContent||'').trim())&&x.getBoundingClientRect().top<160))()"):
                ok = True; break
        if not ok: res["error"] = "video never loaded"; shot(tid, "2-noload"); print(json.dumps(res)); return
        res["reached"] = "video-loaded"; shot(tid, "2-video")
        # 3) 次へ until caption textarea + header シェア appear
        for i in range(4):
            nb = rect_center(tid, """(()=>{const x=[...document.querySelectorAll('div[role=button],button,span,a')].find(e=>['次へ','Next'].includes((e.textContent||'').trim())&&e.getBoundingClientRect().top<160&&e.getBoundingClientRect().height>0);if(!x)return null;const r=x.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
            if nb: cdp.click_xy(tid, nb["x"], nb["y"]); time.sleep(3.5)
            if ev(tid, "(()=>!!(document.querySelector('textarea[aria-label],div[role=textbox][contenteditable=true]')||document.querySelector('textarea')))()"):
                break
        res["reached"] = "caption-step"; shot(tid, "3-caption-step")
        # 4) caption
        cf = rect_center(tid, """(()=>{const t=document.querySelector('textarea[aria-label],div[role=textbox][contenteditable=true]')||document.querySelector('textarea');if(!t)return null;const r=t.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
        if cf: cdp.click_xy(tid, cf["x"], cf["y"]); time.sleep(0.6); cdp.insert_text(tid, caption); time.sleep(1.5)
        res["reached"] = "caption-filled"; shot(tid, "4-caption")
        # 5) header シェア
        sb = rect_center(tid, """(()=>{const el=[...document.querySelectorAll('div[role=button],button,a,span')].find(x=>/^(シェア|Share)$/.test((x.textContent||'').trim())&&x.getBoundingClientRect().top<160&&x.getBoundingClientRect().height>0);if(!el)return null;const r=el.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
        if not sb: res["reached"] = "no-share-btn"; shot(tid, "5-noshare"); print(json.dumps(res)); return
        res["reached"] = "READY"; shot(tid, "5-ready")
        if not a.live:
            cdp.press_key(tid, "Escape", code="Escape", vk=27); time.sleep(1)
            dl = rect_center(tid, """(()=>{const b=[...document.querySelectorAll('button,[role=button]')].find(x=>['破棄','Discard'].includes((x.textContent||'').trim())&&x.offsetParent);if(!b)return null;const r=b.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
            if dl: cdp.click_xy(tid, dl["x"], dl["y"])
            res["reached"] = "DRY-ok"; print(json.dumps(res, ensure_ascii=False)); return
        # LIVE
        cdp.click_xy(tid, sb["x"], sb["y"]); time.sleep(3); shot(tid, "6-sharing")
        url = None
        for _ in range(10):
            time.sleep(12)
            cdp.navigate(tid, f"https://www.instagram.com/{a.handle}/"); time.sleep(5)
            url = ev(tid, """(()=>{const a=document.querySelector('main a[href*="/reel/"],main a[href*="/p/"]');return a?('https://www.instagram.com'+a.getAttribute('href')):null;})()""")
            if url: break
        res["published"] = bool(url); res["post_url"] = url
        res["reached"] = "PUBLISHED" if url else "shared-unconfirmed"; shot(tid, "7-profile")
        if a.delete_after and url:
            res["delete"] = delete_reel(tid, url, a.handle)
    except Exception as e:
        res["error"] = repr(e)[:200]
    finally:
        print(json.dumps(res, ensure_ascii=False))


def delete_reel(tid, url, handle):
    """⋯ → 削除 → confirm. Verifies via post-count returning lower."""
    cdp.navigate(tid, url); time.sleep(6)
    mb = ev(tid, """(()=>{const s=document.querySelector('svg[aria-label="他のオプション"],svg[aria-label="その他のオプション"],svg[aria-label="More options"],svg[aria-label="More"]');if(!s)return null;const r=s.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
    if mb: cdp.click_xy(tid, mb["x"], mb["y"]); time.sleep(2)
    dl = ev(tid, """(()=>{const b=[...document.querySelectorAll('button,[role=button],div[role=button],span')].find(x=>['削除','Delete'].includes((x.textContent||'').trim())&&x.offsetParent);if(!b)return null;const r=b.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
    if dl: cdp.click_xy(tid, dl["x"], dl["y"]); time.sleep(2)
    cf = ev(tid, """(()=>{const b=[...document.querySelectorAll('button,[role=button],div[role=button]')].find(x=>['削除','Delete'].includes((x.textContent||'').trim())&&x.offsetParent&&x.getBoundingClientRect().top>120);if(!b)return null;const r=b.getBoundingClientRect();return{x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)};})()""")
    if cf: cdp.click_xy(tid, cf["x"], cf["y"]); time.sleep(4)
    cdp.navigate(tid, f"https://www.instagram.com/{handle}/"); time.sleep(5)
    tiles = ev(tid, "(()=>[...document.querySelectorAll('main a[href*=\"/reel/\"],main a[href*=\"/p/\"]')].length)()")
    return {"deleted": tiles == 0, "remaining_tiles": tiles}


if __name__ == "__main__":
    main()
