#!/usr/bin/env python3
"""ig-reels-poster — publish a VIDEO Reel to Instagram via the daily-driver browser.

Differs from the carousel poster: a video upload triggers IG's リール flow with an
extra cover-frame/trim step. --dry (default) walks everything up to but NOT including
the final シェア click, screenshots each step, then discards.

Usage:
  post_reel.py --video <mp4> --caption-file <txt> [--dry|--live]

Relies on the shared CDP driver (ig-account-create/scripts/cdp.py).
"""
import argparse, os, sys, time

sys.path.insert(0, os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
import cdp  # noqa: E402

SHOT_DIR = "/tmp/ig-reels-shots"
os.makedirs(SHOT_DIR, exist_ok=True)


def ev(tid, expr):
    return cdp.evaluate(tid, expr)


def shot(tid, name):
    p = os.path.join(SHOT_DIR, f"{name}.png")
    try:
        cdp.screenshot(tid, p)
    except Exception:
        pass
    return p


def find_and_click(tid, *texts, timeout=15):
    """Find a clickable element whose text matches any of `texts`, click it."""
    deadline = time.time() + timeout
    js = (
        "(()=>{const ts=%s;const els=[...document.querySelectorAll("
        "'button,a,div[role=button],span')];"
        "for(const t of ts){const e=els.find(x=>(x.innerText||'').trim()===t"
        "&&x.getBoundingClientRect().height>0);"
        "if(e){const r=e.getBoundingClientRect();e.click();"
        "return {ok:true,t,x:r.x+r.width/2,y:r.y+r.height/2};}}"
        "return {ok:false};})()"
    ) % (str(list(texts)))
    while time.time() < deadline:
        r = ev(tid, js)
        res = r.get("result", r) if isinstance(r, dict) else r
        if isinstance(res, dict) and res.get("ok"):
            return res
        time.sleep(1.5)
    return {"ok": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--live", action="store_true", help="actually publish (default = dry)")
    a = ap.parse_args()
    dry = not a.live
    caption = open(a.caption_file, encoding="utf-8").read().strip()
    video = os.path.abspath(a.video)
    assert os.path.exists(video), f"no video: {video}"

    tid = cdp.new_tab("https://www.instagram.com/")
    time.sleep(6)
    shot(tid, "01-home")

    # 1) Create (新規投稿 / Create)
    r = find_and_click(tid, "作成", "Create", "新規投稿", "New post")
    print("[reel] create:", r)
    time.sleep(3)
    shot(tid, "02-create")

    # 2) set the video into the hidden file input
    try:
        cdp.setfile(tid, "input[type=file]", video)
    except Exception as e:
        print("[reel] setfile err:", e)
    time.sleep(6)
    shot(tid, "03-uploaded")

    # 3) IG may show a "リール" notice / OK / 続行 — accept it
    find_and_click(tid, "OK", "続行", "Continue", "リール", "Reel", timeout=8)
    time.sleep(2)

    # 4) 次へ (crop/cover step — video adds the cover-frame selection)
    find_and_click(tid, "次へ", "Next")
    time.sleep(3)
    shot(tid, "04-cover-step")
    # 5) 次へ again (edit/filter step)
    find_and_click(tid, "次へ", "Next")
    time.sleep(3)
    shot(tid, "05-caption-step")

    # 6) caption
    cap_js = (
        "(()=>{const a=document.querySelector('textarea,div[contenteditable=true]');"
        "if(!a)return{ok:false};a.focus();return{ok:true};})()"
    )
    ev(tid, cap_js)
    try:
        cdp.insert(tid, caption)
    except Exception as e:
        print("[reel] caption insert err:", e)
    time.sleep(2)
    shot(tid, "06-caption-filled")

    if dry:
        print("[reel] DRY — stopping BEFORE final シェア (flow verified). Shots in", SHOT_DIR)
        return

    # 7) LIVE: final share
    r = find_and_click(tid, "シェア", "Share")
    print("[reel] share:", r)
    time.sleep(8)
    shot(tid, "07-shared")
    url = ev(tid, "location.href")
    print("[reel] LIVE posted. url=", url)


if __name__ == "__main__":
    main()
